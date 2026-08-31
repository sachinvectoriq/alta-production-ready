import psycopg2
from azure.cosmos import CosmosClient, exceptions
from dotenv import load_dotenv
import uuid
import os

load_dotenv()

# --- Postgres connection ---
pg_conn = psycopg2.connect(
    dbname=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    host=os.getenv('DB_HOST'),
    port=os.getenv('DB_PORT')
)

# --- Cosmos connection ---
cosmos_client = CosmosClient(os.getenv('COSMOS_ENDPOINT'), os.getenv('COSMOS_KEY'))
container = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME')).get_container_client('user_login_log')

cursor = pg_conn.cursor()
cursor.execute('SELECT "user", login_session_id, login_date_and_time, domain_name FROM user_login_log ORDER BY login_session_id;')

max_session_id = 0
migrated, failed = 0, 0

for user, login_session_id, login_dt, domain_name in cursor.fetchall():
    item = {
        "id": str(uuid.uuid4()),
        "type": "user_login_log",
        "user": user,
        "login_session_id": login_session_id,
        "login_date_and_time": login_dt.isoformat() if login_dt else None,
        "domain_name": domain_name
    }
    try:
        container.create_item(body=item)
        migrated += 1
        max_session_id = max(max_session_id, login_session_id)
    except Exception as e:
        print(f"Failed row (login_session_id={login_session_id}): {e}")
        failed += 1

# Seed the counter document so new inserts continue from the correct value
container.upsert_item({
    "id": "counter_login_session_id",
    "type": "counter",
    "user": "counter_login_session_id",  # must match partition key path value
    "value": max_session_id
})

print(f"Done. Migrated: {migrated}, Failed: {failed}, Counter seeded at: {max_session_id}")

cursor.close()
pg_conn.close()