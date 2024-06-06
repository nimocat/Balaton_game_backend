import pandas as pd
import redis
from fastapi import APIRouter, HTTPException, Depends
from database import redis_client
import logging
import json
from database import db
from models import PurchaseRequest, PurchaseResponse, OpenItemRequest, OpenItemResponse
from game_logic import update_player_items_to_mongo

items = APIRouter()
admin_secret = "admin_secret"
tasks_collection = db.tasks

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@items.post("/items/purchase", response_model=PurchaseResponse, summary="Purchase an item", tags=["Items"])
async def purchase_item(request: PurchaseRequest):
    item_key = f"shop_item:{request.item_id}"
    player_key = f"{request.player_name}_ITEMS"  # Use player_name to construct the player key
    player_token_key = f"{request.player_name}_TOKENS"

    # Check if the item exists and is available
    if not redis_client.exists(item_key):
        raise HTTPException(status_code=404, detail="Item not found")
    
    item_data = redis_client.hgetall(item_key)
    if not bool(int(item_data[b'avaliable'].decode('utf-8'))):
        raise HTTPException(status_code=400, detail="Item not available")

    price = int(item_data[b'price'].decode('utf-8'))
    discount = float(item_data[b'discount'].decode('utf-8'))
    available_stock = int(item_data[b'limit_number'].decode('utf-8'))

    total_cost = int(price * request.purchase_num * (1 - discount))
    print("total_cost is", total_cost)
    # Check if there is enough stock and if the player has enough money
    player_data = redis_client.hgetall(player_key)
    if not player_data:
        raise HTTPException(status_code=404, detail="Player itmes not found")
    player_balance = int(player_data[b'1'].decode('utf-8'))  # Assuming money is stored with ID 1

    if request.purchase_num > available_stock:
        raise HTTPException(status_code=400, detail="Not enough stock")
    
    if total_cost > player_balance:
        raise HTTPException(status_code=400, detail="Not enough balance")

    # Perform the purchase using Redis transactions
    with redis_client.pipeline() as pipe:
        while True:
            try:
                # Watch the keys that will be modified
                pipe.watch(item_key, player_key)

                # Update stock and player balance
                pipe.multi()
                if available_stock != 999:
                    pipe.hincrby(item_key, "num", -request.purchase_num)

                # 减少玩家的代币
                pipe.incrby(player_token_key, -total_cost)
                
                # 增加玩家的items库存
                pipe.hincrby(player_key, str(request.item_id), request.purchase_num)
                pipe.execute()
                break
            except redis.WatchError:
                # If the watched keys were modified, retry the transaction
                continue
    
    update_player_items_to_mongo(request.player_name)

    remaining_balance = player_balance - total_cost
    remaining_stock = available_stock - request.purchase_num if request.purchase_num != 999 else 999

    return PurchaseResponse(
        message="Purchase completed successfully",
        remaining_balance=remaining_balance,
        remaining_stock=remaining_stock
    )

@items.post("/items/open_item", response_model=OpenItemResponse, summary="Open an item", tags=["Items"])
async def open_item(request: OpenItemRequest):
    item_key = f"item:{request.item_id}"
    player_key = f"{request.player_name}_ITEMS"

    # Check if the item exists
    if not redis_client.exists(item_key):
        raise HTTPException(status_code=404, detail="Item not found")

    item_data = redis_client.hgetall(item_key)
    item_type = int(item_data[b'main_type'].decode('utf-8'))

    # Check if the item is a package (type 2)
    if item_type != 2:
        raise HTTPException(status_code=400, detail="Item is not a package")

    # Get the effect of the item
    effect = json.loads(item_data[b'effect'].decode('utf-8'))

    # Calculate the obtained items
    obtained_items = {}
    for sub_item_id, num in effect:
        total_num = num * request.item_num
        if sub_item_id in obtained_items:
            obtained_items[sub_item_id] += total_num
        else:
            obtained_items[sub_item_id] = total_num

    # Perform the operation using Redis transactions
    with redis_client.pipeline() as pipe:
        while True:
            try:
                # Watch the keys that will be modified
                pipe.watch(player_key)

                # Check if the player has enough items to open
                player_items = redis_client.hgetall(player_key)
                if not player_items:
                    raise HTTPException(status_code=404, detail="Player itmes not found")
                player_balance = int(player_items.get(request.item_id.encode('utf-8'), b'0').decode('utf-8'))
                if player_balance < request.item_num:
                    raise HTTPException(status_code=400, detail="Not enough items to open")

                # Update player's items
                pipe.multi()
                pipe.hincrby(player_key, str(request.item_id), -request.item_num)
                for sub_item_id, num in obtained_items.items():
                    pipe.hincrby(player_key, str(sub_item_id), num)
                pipe.execute()
                break
            except redis.WatchError:
                # If the watched keys were modified, retry the transaction
                continue

    return OpenItemResponse(
        message="Items opened successfully",
        obtained_items=obtained_items
    )

