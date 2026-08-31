import psycopg2
from azure.cosmos import CosmosClient
from dotenv import load_dotenv
import os

load_dotenv()

pg_conn = psycopg2.connect(
    dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'), host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT')
)
cosmos_client = CosmosClient(os.getenv('COSMOS_ENDPOINT'), os.getenv('COSMOS_KEY'))
container = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME')).get_container_client('deepl_settings')

cursor = pg_conn.cursor()
cursor.execute("SELECT admin_id, api_key FROM deepl_settings ORDER BY admin_id;")

migrated, failed = 0, 0

for admin_id, api_key in cursor.fetchall():
    item = {
        "id": admin_id,   # matches admin_id directly -- point reads/writes, no query needed
        "type": "deepl_settings",
        "admin_id": admin_id,
        "api_key": api_key
    }
    try:
        container.create_item(body=item)
        migrated += 1
    except Exception as e:
        print(f"Failed row (admin_id={admin_id}): {e}")
        failed += 1

print(f"Done. Migrated: {migrated}, Failed: {failed}")

cursor.close()
pg_conn.close()