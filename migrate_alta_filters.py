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
container = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME')).get_container_client('alta_filters')

cursor = pg_conn.cursor()
cursor.execute("""
    SELECT id, modifier, value, system_prompt, user_prompt,
           created_by, created_at, updated_at, sequence, status
    FROM alta_filters ORDER BY id;
""")

max_id = 0
migrated, failed = 0, 0

for row in cursor.fetchall():
    (fid, modifier, value, system_prompt, user_prompt,
     created_by, created_at, updated_at, sequence, status) = row

    item = {
        "id": str(uuid.uuid4()),
        "type": "alta_filters",
        "filter_id": fid,
        "modifier": modifier,
        "value": value,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "created_by": created_by,
        "created_at": created_at.isoformat() if created_at else None,
        "updated_at": updated_at.isoformat() if updated_at else None,
        "sequence": sequence,
        "status": status
    }
    try:
        container.create_item(body=item)
        migrated += 1
        max_id = max(max_id, fid)
    except Exception as e:
        print(f"Failed row (id={fid}): {e}")
        failed += 1

# Seed the counter for filter_id (separate from the 'sequence' business field)
container.upsert_item({
    "id": "counter_filter_id",
    "type": "counter",
    "modifier": "__counter__",   # matches partition key path so it's independently addressable
    "value": max_id
})

print(f"Done. Migrated: {migrated}, Failed: {failed}, Counter seeded at: {max_id}")

cursor.close()
pg_conn.close()