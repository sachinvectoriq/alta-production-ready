import psycopg2
from azure.cosmos import CosmosClient
from dotenv import load_dotenv
import uuid
import os

load_dotenv()

pg_conn = psycopg2.connect(
    dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'), host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT')
)
cosmos_client = CosmosClient(os.getenv('COSMOS_ENDPOINT'), os.getenv('COSMOS_KEY'))
container = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME')).get_container_client('alta_var_settings')

cursor = pg_conn.cursor()
cursor.execute("SELECT key, value FROM alta_var_settings;")

migrated, failed = 0, 0

for key, value in cursor.fetchall():
    item = {
        "id": str(uuid.uuid4()),
        "type": "alta_var_settings",
        "key": key,
        "value": value
    }
    try:
        container.create_item(body=item)
        migrated += 1
    except Exception as e:
        print(f"Failed row (key={key}): {e}")
        failed += 1

print(f"Done. Migrated: {migrated}, Failed: {failed}")

cursor.close()
pg_conn.close()