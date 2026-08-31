from azure.cosmos import CosmosClient, PartitionKey
from dotenv import load_dotenv
import os

load_dotenv()

client = CosmosClient(os.getenv('COSMOS_ENDPOINT'), os.getenv('COSMOS_KEY'))

database = client.create_database_if_not_exists(id=os.getenv('COSMOS_DB_NAME'))
print(f"Database ready: {database.id}")

container = database.create_container_if_not_exists(
    id='user_login_log',
    partition_key=PartitionKey(path='/user')
    # no offer_throughput passed — if your account is Serverless this is required to be omitted;
    # if it's Provisioned, tell me and I'll add offer_throughput=400
)
print(f"Container ready: {container.id}")