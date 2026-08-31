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
container = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME')).get_container_client('user_feedback')

cursor = pg_conn.cursor()
cursor.execute("""
    SELECT user_name, feedback_text, source_language, target_language, document_name,
           source_text, translated_text, vendor, feedback_id, feedback_date_and_time,
           glossary_filename, domain_name
    FROM user_feedback ORDER BY feedback_id;
""")

max_id = 0
migrated, failed = 0, 0

for row in cursor.fetchall():
    (user_name, feedback_text, source_language, target_language, document_name,
     source_text, translated_text, vendor, feedback_id, feedback_dt,
     glossary_filename, domain_name) = row

    item = {
        "id": str(uuid.uuid4()),
        "type": "user_feedback",
        "user_name": user_name,
        "feedback_text": feedback_text,
        "source_language": source_language,
        "target_language": target_language,
        "document_name": document_name,
        "source_text": source_text,
        "translated_text": translated_text,
        "vendor": vendor,
        "feedback_id": feedback_id,
        "feedback_date_and_time": feedback_dt.isoformat() if feedback_dt else None,
        "glossary_filename": glossary_filename,
        "domain_name": domain_name
    }
    try:
        container.create_item(body=item)
        migrated += 1
        max_id = max(max_id, feedback_id)
    except Exception as e:
        print(f"Failed row (feedback_id={feedback_id}): {e}")
        failed += 1

# Seed counter for feedback_id
container.upsert_item({
    "id": "counter_feedback_id",
    "type": "counter",
    "user_name": "__counter__",   # matches partition key path, keeps counter isolated
    "value": max_id
})

print(f"Done. Migrated: {migrated}, Failed: {failed}, Counter seeded at: {max_id}")

cursor.close()
pg_conn.close()