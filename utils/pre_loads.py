# read the design_docs/GameItems.xlsx, use database.py's redis client to load item_id, main_type, sub_type, effect into redis
import pandas as pd
from database import redis_client
import logging

logger = logging.getLogger(__name__)

def load_game_items():
    # Load the data from Excel file
    df = pd.read_excel('design_docs/GameItems.xlsx')
    
    # Use a Redis pipeline to batch the operations and reduce the number of round trips to the server
    with redis_client.pipeline() as pipe:
        for _, row in df.iterrows():
            # Construct the Redis key using item_id
            key = f"item:{row['item_id']}"
            # Create a dictionary of the item attributes to be stored
            item_data = {
                'main_type': row['main_type'],
                'sub_type': row['sub_type'],
                'effect': row['effect']
            }
            # Store the item data in Redis
            pipe.hmset(key, item_data)
        # Execute all commands in the batch
        pipe.execute()

    logger.info("Game items loaded into Redis successfully.")

def load_shop_items():
    # Load the data from Excel file
    shop_df = pd.read_excel('design_docs/Shop.xlsx')
    
    # Use a Redis pipeline to batch the operations and reduce the number of round trips to the server
    with redis_client.pipeline() as pipe:
        for _, row in shop_df.iterrows():
            # Construct the Redis key using item_id
            key = f"shop_item:{row['id']}"
            # Create a dictionary of the shop item attributes to be stored
            shop_item_data = {
                'goods': row['goods'],
                'price': row['price'],
                'discount': row['discount'],
                'avaliable': row['avaliable'],
                'limit_type': row['limit_type'],
                'limit_number': row['limit_number']
            }
            # Store the shop item data in Redis
            pipe.hmset(key, shop_item_data)
        # Execute all commands in the batch
        pipe.execute()

    logger.info("Shop items loaded into Redis successfully.")

def load_data_from_files():
    # Load game items first
    load_game_items()
    # Add other data loading functions here in the sequence they need to be loaded
    load_shop_items()
