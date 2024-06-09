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

def load_checkin():
    # Load the data from Excel file
    checkin_df = pd.read_excel('design_docs/checkin.xlsx')
    
    # Use a Redis pipeline to batch the operations and reduce the number of round trips to the server
    with redis_client.pipeline() as pipe:
        for _, row in checkin_df.iterrows():
            # Extract data from the row
            task_id = int(row['id'])
            checkpoint = int(row['checkpoint'])
            type = int(row['type'])
            rewards = str(row['reward'])
            
            # Construct the Redis key using type
            key = f"checkin:{type}"
            # Construct the field-value pair where task_id is the field and checkpoint:rewards is the value
            field_value = f"{checkpoint}:{rewards}"
            
            # Use Redis' HSET to store the checkin data with the key, field (task_id), and value (checkpoint:rewards)
            pipe.hset(key, task_id, field_value)
        
        # Execute all commands in the batch
        pipe.execute()

    logger.info("Check-in data loaded into Redis successfully.")


def load_data_from_files():
    # Load game items first
    load_game_items()
    # Add other data loading functions here in the sequence they need to be loaded
    load_shop_items()

    load_checkin()
