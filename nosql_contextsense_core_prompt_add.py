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
container = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME')).get_container_client('contextsense_core_prompt')


def validate_bearer_token(request, expected_token):
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({"error": "Invalid or missing Authorization header."}), 401
    token = auth_header.split(' ')[1]
    if token != expected_token:
        return jsonify({"error": "Unauthorized. Invalid Bearer token."}), 403
    return None


def get_next_core_prompt_id():
    while True:
        counter = container.read_item(item='counter_core_prompt_id', partition_key='__counter__')
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


@app.route('/add_prompt', methods=['GET'])
def add_prompt():
    auth_error = validate_bearer_token(request, 'A7x!G2p@Q9#L')
    if auth_error:
        return auth_error

    prompt = request.args.get('prompt')
    created_by = request.args.get('created_by', None)

    if not prompt:
        return jsonify({"error": "prompt is required"}), 400

    try:
        core_prompt_id = get_next_core_prompt_id()

        item = {
            "id": str(core_prompt_id),
            "type": "contextsense_core_prompt",
            "core_prompt_id": core_prompt_id,
            "prompt": prompt,
            "created_by": created_by,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        container.create_item(body=item)

        return jsonify({"message": "Prompt added successfully"}), 201

    except exceptions.CosmosHttpResponseError as e:
        return jsonify({"error": str(e.message)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)