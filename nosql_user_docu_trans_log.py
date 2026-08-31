from flask import Flask, request, jsonify
from azure.cosmos import CosmosClient, exceptions
from azure.core import MatchConditions
from dotenv import load_dotenv
import pytz
from datetime import datetime
import uuid
import os

load_dotenv()

app = Flask(__name__)

cosmos_client = CosmosClient(os.getenv('COSMOS_ENDPOINT'), os.getenv('COSMOS_KEY'))
database = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME'))
container = database.get_container_client('user_docu_trans_log')


def get_next_log_id():
    while True:
        counter = container.read_item(item='counter_log_id', partition_key='__counter__')
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


@app.route('/log_document_translation', methods=['POST'])
def log_document_translation():
    """
    Endpoint to log user document translation details.
    Expects form data: 'user', 'document_name', 'source_language', 'target_language', 
                         'billed_characters', 'size_of_the_document', 'vendor'.
    """
    user = request.form.get('user')
    document_name = request.form.get('document_name')
    source_language = request.form.get('source_language')
    target_language = request.form.get('target_language')
    billed_characters = request.form.get('billed_characters')
    size_of_the_document = request.form.get('size_of_the_document')
    vendor = request.form.get('vendor')
    domain_name = request.form.get('domain_name', False)
    login_session_id = request.form.get('login_session_id')

    if not user or not document_name or not source_language or not target_language or not vendor or not login_session_id:
        return jsonify({"error": "The 'user', 'document_name', 'source_language', 'target_language', 'vendor', and 'login_session_id' fields are required."}), 400

    try:
        billed_characters = int(billed_characters) if billed_characters else None
        size_of_the_document = int(size_of_the_document) if size_of_the_document else None
        login_session_id = int(login_session_id) if login_session_id else None
    except ValueError:
        return jsonify({"error": "billed_characters, size_of_the_document, and login_session_id must be integers."}), 400

    utc_now = datetime.utcnow()
    eastern = pytz.timezone('America/New_York')
    eastern_time = pytz.utc.localize(utc_now).astimezone(eastern)

    try:
        log_id = get_next_log_id()

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
            "date_and_time": eastern_time.isoformat(),
            "log_id": log_id,
            "glossary_filename": None,
            "login_session_id": login_session_id,
            "domain_name": domain_name if domain_name else None
        }

        container.create_item(body=item)

        return jsonify({"message": "Document translation details logged successfully."}), 201

    except exceptions.CosmosHttpResponseError as e:
        return jsonify({"error": f"Database error: {e.message}"}), 500


if __name__ == '__main__':
    app.run(debug=True)