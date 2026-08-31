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
container = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME')).get_container_client('contextsense_core_prompt')

cursor = pg_conn.cursor()
cursor.execute("""
    SELECT core_prompt_id, prompt, created_by, created_at
    FROM contextsense_core_prompt ORDER BY core_prompt_id;
""")

max_id = 0
migrated, failed = 0, 0

for row in cursor.fetchall():
    core_prompt_id, prompt, created_by, created_at = row

    item = {
        "id": str(core_prompt_id),   # matches core_prompt_id directly -- enables point reads/deletes
        "type": "contextsense_core_prompt",
        "core_prompt_id": core_prompt_id,
        "prompt": prompt,
        "created_by": created_by,
        "created_at": created_at.isoformat() if created_at else None
    }
    try:
        container.create_item(body=item)
        migrated += 1
        max_id = max(max_id, core_prompt_id)
    except Exception as e:
        print(f"Failed row (core_prompt_id={core_prompt_id}): {e}")
        failed += 1

container.upsert_item({
    "id": "counter_core_prompt_id",
    "type": "counter",
    "core_prompt_id": "__counter__",
    "value": max_id
})

print(f"Done. Migrated: {migrated}, Failed: {failed}, Counter seeded at: {max_id}")

cursor.close()
pg_conn.close()