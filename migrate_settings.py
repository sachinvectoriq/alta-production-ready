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
container = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME')).get_container_client('settings')

cursor = pg_conn.cursor()
cursor.execute("""
    SELECT admin_id, key, text_translation_endpoint, document_translation_endpoint,
           region, storage_connection_string
    FROM settings ORDER BY admin_id;
""")

max_id = 0
migrated, failed = 0, 0

for row in cursor.fetchall():
    admin_id, key, text_ep, doc_ep, region, conn_str = row

    item = {
        "id": str(admin_id),   # matches admin_id directly -- point reads/writes, no query needed
        "type": "settings",
        "admin_id": admin_id,
        "key": key,
        "text_translation_endpoint": text_ep,
        "document_translation_endpoint": doc_ep,
        "region": region,
        "storage_connection_string": conn_str
    }
    try:
        container.create_item(body=item)
        migrated += 1
        max_id = max(max_id, admin_id)
    except Exception as e:
        print(f"Failed row (admin_id={admin_id}): {e}")
        failed += 1

container.upsert_item({
    "id": "counter_admin_id",
    "type": "counter",
    "admin_id": "__counter__",
    "value": max_id
})

print(f"Done. Migrated: {migrated}, Failed: {failed}, Counter seeded at: {max_id}")

cursor.close()
pg_conn.close()