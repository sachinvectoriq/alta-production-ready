from azure.cosmos import CosmosClient, PartitionKey
from dotenv import load_dotenv
import os

load_dotenv()

client = CosmosClient(os.getenv('COSMOS_ENDPOINT'), os.getenv('COSMOS_KEY'))
database = client.get_database_client(os.getenv('COSMOS_DB_NAME'))

container = database.create_container_if_not_exists(
    id='contextsense_core_prompt',
    partition_key=PartitionKey(path='/core_prompt_id')
)
print(f"Container ready: {container.id}")