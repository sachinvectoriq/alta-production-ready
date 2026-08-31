from flask import request, jsonify
from azure.cosmos import CosmosClient, exceptions
from dotenv import load_dotenv
import os

load_dotenv()

cosmos_client = CosmosClient(os.getenv('COSMOS_ENDPOINT'), os.getenv('COSMOS_KEY'))
container = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME')).get_container_client('deepl_settings')


def validate_bearer_token(request, expected_token):
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({"error": "Invalid or missing Authorization header."}), 401
    token = auth_header.split(' ')[1]
    if token != expected_token:
        return jsonify({"error": "Unauthorized. Invalid Bearer token."}), 403
    return None


def save_settings_deepl_secure():
    auth_error = validate_bearer_token(request, 'A7x!G2p@Q9#L')
    if auth_error:
        return auth_error

    if 'admin_id' not in request.form or 'api_key' not in request.form:
        return jsonify({"error": "Missing admin_id or api_key"}), 400

    admin_id = request.form['admin_id']
    api_key = request.form['api_key']

    try:
        item = {
            "id": admin_id,
            "type": "deepl_settings",
            "admin_id": admin_id,
            "api_key": api_key
        }
        # upsert_item natively replicates INSERT ... ON CONFLICT DO UPDATE
        container.upsert_item(body=item)
        return jsonify({"message": "Settings saved successfully!"}), 200

    except exceptions.CosmosHttpResponseError as e:
        return jsonify({"error": str(e.message)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500