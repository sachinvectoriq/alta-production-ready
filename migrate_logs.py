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
container = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME')).get_container_client('logs')

cursor = pg_conn.cursor()
cursor.execute('SELECT id, "timestamp", level, log, data, session_id FROM logs ORDER BY id;')

migrated, failed = 0, 0

for row in cursor.fetchall():
    log_id, ts, level, log_text, data, session_id = row

    item = {
        "id": str(uuid.uuid4()),
        "type": "logs",
        "log_id": log_id,                                # preserved original integer id, for reference/audit only
        "timestamp": ts.isoformat() if ts else None,
        "log_date": ts.strftime('%Y-%m-%d') if ts else None,   # partition key value
        "level": level,
        "log": log_text,
        "data": data,                                     # stored as native JSON object, not a string
        "session_id": str(session_id) if session_id else None
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