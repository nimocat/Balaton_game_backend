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

def load_quest_items():
    # Load the data from Excel file
    quest_df = pd.read_excel('design_docs/Quest.xlsx')
    
    # Use a Redis pipeline to batch the operations and reduce the number of round trips to the server
    with redis_client.pipeline() as pipe:
        for _, row in quest_df.iterrows():
            # Construct the Redis key using quest_id
            key = f"quest:{row['Id']}"
            # Create a dictionary of the quest attributes to be stored
            quest_data = {
                'type': row['type'],
                'prohibility': row['prohibility'],
                'num': row['num']
            }
            # Store the quest data in Redis
            pipe.hmset(key, quest_data)
        # Execute all commands in the batch
        pipe.execute()

    logger.info("Quest items loaded into Redis successfully.")


# load checkin表，目前也是task表，存储后，一个是id -> info map，一个是type -> [task_id] set。通过id查询信息，通过type查询id
def load_quest():
    # Load the data from Excel file
    checkin_df = pd.read_excel('design_docs/Quest.xlsx')
    
    # Use a Redis pipeline to batch the operations and reduce the number of round trips to the server
    # 以type为分类
    with redis_client.pipeline() as pipe:
        for _, row in checkin_df.iterrows():
            # Extract data from the row
            task_id = int(row['id'])
            checkpoint = int(row['checkpoint'])
            type = int(row['type'])
            rewards = str(row['reward'])
            repeat = str(row['repeat'])
            settlement_type = str(row['settlement_type'])

            # Construct the Redis key using task_id
            key = f"task:{task_id}"
            # Create a dictionary of the remaining data to be stored
            quest_data = {
                'checkpoint': checkpoint,
                'type': type,
                'rewards': rewards,
                'repeat': repeat,
                'settlement_type': settlement_type
            }
            # Store the checkin data in Redis
            pipe.hmset(key, quest_data)

            # Construct the Redis key using type
            key = f"task_type:{type}"
            # Store the task_id under the constructed key
            pipe.sadd(key, task_id)
        
        # Execute all commands in the batch
        pipe.execute()

    logger.info("Quest data loaded into Redis successfully.")


def load_settlement():
    # Load the data from Excel file
    settlement_df = pd.read_excel('design_docs/Settlement.xlsx')
    
    # Use a Redis pipeline to batch the operations and reduce the number of round trips to the server
    with redis_client.pipeline() as pipe:
        for _, row in settlement_df.iterrows():
            # Extract data from the row
            settlement_id = int(row['id'])
            type = int(row['type'])
            name = str(row['name'])
            buttom = str(row['buttom'])
            mul = float(row['mul'])
            special = str(row['special'])
            random = str(row['random'])

            # Construct the Redis key using settlement_id
            key = f"settlement:{settlement_id}"
            # Create a dictionary of the remaining data to be stored
            settlement_data = {
                'type': type,
                'name': name,
                'buttom': buttom,
                'mul': mul,
                'special': special,
                'random': random
            }
            # Store the settlement data in Redis
            pipe.hmset(key, settlement_data)

            # Construct the Redis key using type
            key = f"settlement_type:{type}"
            # Store the settlement_id under the constructed key
            pipe.sadd(key, settlement_id)
        
        # Execute all commands in the batch
        pipe.execute()

    logger.info("Settlement data loaded into Redis successfully.")



def load_data_from_files():
    # Load game items first
    # 首先加载游戏物品
    load_game_items()
    # Add other data loading functions here in the sequence they need to be loaded
    # 按照需要加载的顺序在此处添加其他数据加载函数
    load_shop_items()
    # 加载商店物品
    load_quest()
    # 加载任务
    load_settlement()
    # 加载结算表