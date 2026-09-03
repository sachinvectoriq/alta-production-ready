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
container = database.get_container_client('user_text_trans_log')


def get_next_log_id():
    """Atomically increments the counter document for log_id."""
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


@app.route('/log_text_translation', methods=['POST'])
def log_text_translation():
    """
    Endpoint to log user text translation details.
    Expects form data input: 
    'user', 'source_text', 'translated_text', 'source_language', 'target_language', 'billed_characters', 'vendor'
    """
    user = request.form.get('user')
    source_text = request.form.get('source_text')
    translated_text = request.form.get('translated_text')
    source_language = request.form.get('source_language')
    target_language = request.form.get('target_language')
    billed_characters = request.form.get('billedd_characters')  # form field name kept as-is (typo preserved intentionally)
    vendor = request.form.get('vendor')
    domain_name = request.form.get('domain_name', False)

    refinement_used_str = request.form.get('refinement_used', 'false').lower()
    refinement_used = refinement_used_str in ('true', 'yes', '1', 't', 'y')

    login_session_id = request.form.get('login_session_id')
    if login_session_id is not None:
        try:
            login_session_id = int(login_session_id)
        except ValueError:
            return jsonify({"error": "login_session_id must be an integer."}), 400

    if not user or not source_text or not translated_text:
        return jsonify({"error": "The 'user', 'source_text', and 'translated_text' fields are required."}), 400

    utc_now = datetime.utcnow()
    eastern = pytz.timezone('America/New_York')
    eastern_time = pytz.utc.localize(utc_now).astimezone(eastern)

    try:
        log_id = get_next_log_id()

        item = {
            "id": str(uuid.uuid4()),
            "type": "user_text_trans_log",
            "user": user,
            "source_text": source_text,
            "translated_text": translated_text,
            "source_language": source_language,
            "target_language": target_language,
            "billed_characters": billed_characters,
            "vendor": vendor,
            "date_and_time": eastern_time.isoformat(),
            "log_id": log_id,
            "refinement_used": refinement_used,
            "login_session_id": login_session_id,
            "domain_name": domain_name if domain_name else None
        }

        container.create_item(body=item)

        return jsonify({"message": "Text translation details logged successfully.",
                        "log_id": log_id,
                        "login_session_id": login_session_id}), 201

    except exceptions.CosmosHttpResponseError as e:
        return jsonify({"error": f"Database error: {e.message}"}), 500


if __name__ == '__main__':
    app.run(debug=True)