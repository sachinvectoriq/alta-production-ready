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
container = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME')).get_container_client('user_docu_trans_log')

cursor = pg_conn.cursor()
cursor.execute('''
    SELECT "user", document_name, source_language, target_language, billed_characters,
           size_of_the_document, vendor, date_and_time, log_id, glossary_filename,
           login_session_id, domain_name
    FROM user_docu_trans_log ORDER BY log_id;
''')

max_id = 0
migrated, failed = 0, 0

for row in cursor.fetchall():
    (user, document_name, source_language, target_language, billed_characters,
     size_of_the_document, vendor, date_and_time, log_id, glossary_filename,
     login_session_id, domain_name) = row

    item = {
        "id": str(uuid.uuid4()),
        "type": "user_docu_trans_log",
        "user": user,
        "document_name": document_name,
        "source_language": source_language,
        "target_language": target_language,
        "billed_characters": billed_characters,
        "size_of_the_document": size_of_the_document,
        "vendor": vendor,
        "date_and_time": date_and_time.isoformat() if date_and_time else None,
        "log_id": log_id,
        "glossary_filename": glossary_filename,
        "login_session_id": login_session_id,
        "domain_name": domain_name
    }
    try:
        container.create_item(body=item)
        migrated += 1
        max_id = max(max_id, log_id)
    except Exception as e:
        print(f"Failed row (log_id={log_id}): {e}")
        failed += 1

container.upsert_item({
    "id": "counter_log_id",
    "type": "counter",
    "login_session_id": "__counter__",
    "value": max_id
})

print(f"Done. Migrated: {migrated}, Failed: {failed}, Counter seeded at: {max_id}")

cursor.close()
pg_conn.close()