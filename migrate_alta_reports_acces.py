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
container = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME')).get_container_client('alta_reports_access')

cursor = pg_conn.cursor()
cursor.execute("SELECT id, name, email, permission_granted_at, granted_by FROM alta_reports_access ORDER BY id;")

max_id = 0
migrated, failed = 0, 0

for row in cursor.fetchall():
    record_id, name, email, granted_at, granted_by = row

    item = {
        "id": str(uuid.uuid4()),
        "type": "alta_reports_access",
        "access_id": record_id,
        "name": name,
        "email": email,
        "permission_granted_at": granted_at.isoformat() if granted_at else None,
        "granted_by": granted_by
    }
    try:
        container.create_item(body=item)
        migrated += 1
        max_id = max(max_id, record_id)
    except Exception as e:
        print(f"Failed row (id={record_id}): {e}")
        failed += 1

# Seed counter for access_id
container.upsert_item({
    "id": "counter_access_id",
    "type": "counter",
    "email": "__counter__",   # matches partition key path, keeps counter isolated
    "value": max_id
})

print(f"Done. Migrated: {migrated}, Failed: {failed}, Counter seeded at: {max_id}")

cursor.close()
pg_conn.close()