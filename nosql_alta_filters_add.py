from flask import Flask, request, jsonify
from azure.cosmos import CosmosClient, exceptions
from azure.core import MatchConditions
from dotenv import load_dotenv
from datetime import datetime, timezone
import uuid
import os

load_dotenv()

app = Flask(__name__)

cosmos_client = CosmosClient(os.getenv('COSMOS_ENDPOINT'), os.getenv('COSMOS_KEY'))
database = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME'))
container = database.get_container_client('alta_filters')

DEFAULT_SYSTEM_PROMPT = "The following portion of the prompt may have contradictory statements which require you to have the context which best matches the majority of the statements: You are communicating with someone in a country which speaks {target_language}."
DEFAULT_USER_PROMPT = (
    "The {modifier_value} of what you are preparing is {user_defined}. "
    "The edits should take into account the {user_defined} context in {target_language} using wording and jargon appropriate to the context, "
    "however, the meaning of the text in {source_language} needs to remain."
)


def validate_bearer_token(request, expected_token):
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({"error": "Invalid or missing Authorization header."}), 401
    token = auth_header.split(' ')[1]
    if token != expected_token:
        return jsonify({"error": "Unauthorized. Invalid Bearer token."}), 403
    return None


def get_next_filter_id():
    """Atomically increments the counter document for filter_id."""
    while True:
        counter = container.read_item(item='counter_filter_id', partition_key='__counter__')
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


def get_next_sequence():
    """Replicates SELECT MAX(sequence) FROM alta_filters + 1, matching original behavior."""
    query = "SELECT VALUE MAX(c.sequence) FROM c WHERE c.type = 'alta_filters'"
    results = list(container.query_items(query=query, enable_cross_partition_query=True))
    max_sequence = results[0] if results and results[0] is not None else 0
    return max_sequence + 1


def insert_into_alta_filters(modifier, value, system_prompt, user_prompt, created_by, sequence, status):
    try:
        if sequence is None:
            sequence = get_next_sequence()
        else:
            sequence = int(sequence)

        current_time = datetime.now(timezone.utc).isoformat()
        filter_id = get_next_filter_id()

        item = {
            "id": str(uuid.uuid4()),
            "type": "alta_filters",
            "filter_id": filter_id,
            "modifier": modifier,
            "value": value,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "created_by": created_by,
            "created_at": current_time,
            "updated_at": current_time,
            "sequence": sequence,
            "status": status
        }

        container.create_item(body=item)

        return True, {
            "id": filter_id,
            "modifier": modifier,
            "value": value,
            "system": system_prompt,
            "user": user_prompt,
            "sequence": sequence,
            "status": status
        }, "Record inserted successfully"

    except exceptions.CosmosHttpResponseError as error:
        return False, None, f"Database error: {error.message}"


@app.route('/api/alta_filters', methods=['POST'])
def add_alta_filter():
    auth_error = validate_bearer_token(request, 'A7x!G2p@Q9#L')
    if auth_error:
        return auth_error

    modifier = request.args.get('modifier')
    value = request.args.get('value', 'User defined')
    created_by = request.args.get('created_by')
    sequence = request.args.get('sequence', None)
    status = request.args.get('status', 'active')

    system_prompt = request.args.get('system_prompt', DEFAULT_SYSTEM_PROMPT)
    user_prompt = request.args.get('user_prompt', DEFAULT_USER_PROMPT)

    if not modifier:
        return jsonify({"success": False, "error": "Missing required field: 'modifier' is mandatory."}), 400

    if user_prompt == DEFAULT_USER_PROMPT:
        user_prompt = user_prompt.replace("{modifier_value}", modifier)

    success, record, message = insert_into_alta_filters(
        modifier, value, system_prompt, user_prompt, created_by, sequence, status
    )

    if success:
        return jsonify({"data": record, "message": message, "success": True}), 201
    else:
        return jsonify({"success": False, "error": message}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)