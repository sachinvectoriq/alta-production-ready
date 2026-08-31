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
container = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME')).get_container_client('alta_logs')

cursor = pg_conn.cursor()
cursor.execute('SELECT id, "timestamp", level, message, data, user_name FROM alta_logs ORDER BY id;')

migrated, failed = 0, 0

for row in cursor.fetchall():
    log_id, ts, level, message, data, user_name = row

    item = {
        "id": str(uuid.uuid4()),
        "type": "alta_logs",
        "log_id": log_id,
        "timestamp": ts.isoformat() if ts else None,
        "log_date": ts.strftime('%Y-%m-%d') if ts else None,  # partition key value
        "level": level,
        "message": message,
        "data": data,          # jsonb -> native nested object, not stringified
        "user_name": user_name
    }
    try:
        container.create_item(body=item)
        migrated += 1
    except Exception as e:
        print(f"Failed row (id={log_id}): {e}")
        failed += 1

print(f"Done. Migrated: {migrated}, Failed: {failed}")

cursor.close()
pg_conn.close()