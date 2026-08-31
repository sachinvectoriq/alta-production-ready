from flask import jsonify
from azure.cosmos import CosmosClient, exceptions
from azure.core import MatchConditions
from logging_config import log, flush
from dotenv import load_dotenv
from datetime import datetime, timezone
import re
import traceback
import uuid
import os

load_dotenv()

cosmos_client = CosmosClient(os.getenv('COSMOS_ENDPOINT'), os.getenv('COSMOS_KEY'))
database = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME'))
container = database.get_container_client('user_feedback')


def get_next_feedback_id():
    while True:
        counter = container.read_item(item='counter_feedback_id', partition_key='__counter__')
        next_val = counter['value'] + 1
        counter['value'] = next_val
        try:
            container.replace_item(
                item=counter,
                body=counter,
                etag=counter['_etag'],
                match_condition=MatchConditions.IfNotModified
            )
            return next_val
        except exceptions.CosmosAccessConditionFailedError:
            continue


def clean_user_name(user_name):
    """
    Replicates the 'user_name_cleanup' trigger -> remove_curly_braces_and_quotes().
    Confirmed against actual Postgres source: strips { } and " only.
    """
    if not user_name:
        return user_name
    return re.sub(r'[{"}]', '', user_name)


def store_feedback(feedback_data):
    log('INFO', "Attempting to store feedback data in the database.",
        data={'feedback_keys': list(feedback_data.keys())})
    """Store user feedback in Cosmos."""
    user_name = feedback_data.get('user_name')
    feedback_text = feedback_data.get('feedback_text')
    source_language = feedback_data.get('source_language') or 'unknown'
    target_language = feedback_data.get('target_language')
    document_name = feedback_data.get('document_name')
    source_text = feedback_data.get('source_text')
    translated_text = feedback_data.get('translated_text')
    vendor = feedback_data.get('vendor')
    glossary_filename = feedback_data.get('glossary_filename')
    domain_name = feedback_data.get('domain_name', False)

    user_name = clean_user_name(user_name)

    try:
        log('INFO', 'Connecting to Cosmos for feedback storage.')

        feedback_id = get_next_feedback_id()

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
            "feedback_date_and_time": datetime.now(timezone.utc).isoformat(),
            "glossary_filename": glossary_filename,
            "domain_name": domain_name if domain_name else None
        }

        log('INFO', "Executing insert for user feedback.",
            data={'user_name': user_name, 'document_name': document_name, 'vendor': vendor})

        container.create_item(body=item)

        log('INFO', "Feedback stored successfully.", user_name=user_name)
        flush()
        return jsonify({"message": "Feedback added successfully"}), 201

    except exceptions.CosmosHttpResponseError as db_error:
        error_traceback = traceback.format_exc()
        log('ERROR',
            f"Database error storing feedback: {db_error}",
            data={'user_name': user_name, 'document_name': document_name, 'traceback': error_traceback})
        flush()
        return jsonify({"error": f"Database error: {str(db_error.message)}"}), 500
    except Exception as e:
        error_traceback = traceback.format_exc()
        log('CRITICAL',
            f"An unexpected error occurred while storing feedback: {e}",
            data={'user_name': user_name, 'document_name': document_name, 'traceback': error_traceback})
        flush()
        return jsonify({"error": str(e)}), 500