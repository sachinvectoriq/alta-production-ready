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
container = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME')).get_container_client('contextsense')

cursor = pg_conn.cursor()
cursor.execute("""
    SELECT selection_id, login_session_id, modifier_type, modifier_value,
           system_prompt, user_prompt, refined_text, explanation, domain_name
    FROM contextsense ORDER BY selection_id;
""")

max_id = 0
migrated, failed = 0, 0

for row in cursor.fetchall():
    (sel_id, login_session_id, modifier_type, modifier_value,
     system_prompt, user_prompt, refined_text, explanation, domain_name) = row

    item = {
        "id": str(uuid.uuid4()),
        "type": "contextsense",
        "selection_id": sel_id,
        "login_session_id": login_session_id,
        "modifier_type": modifier_type,
        "modifier_value": modifier_value,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "refined_text": refined_text,
        "explanation": explanation,
        "domain_name": domain_name
    }
    try:
        container.create_item(body=item)
        migrated += 1
        max_id = max(max_id, sel_id)
    except Exception as e:
        print(f"Failed row (selection_id={sel_id}): {e}")
        failed += 1

container.upsert_item({
    "id": "counter_selection_id",
    "type": "counter",
    "login_session_id": "__counter__",
    "value": max_id
})

print(f"Done. Migrated: {migrated}, Failed: {failed}, Counter seeded at: {max_id}")

cursor.close()
pg_conn.close()