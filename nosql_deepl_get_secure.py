from flask import Flask, request, jsonify
from azure.cosmos import CosmosClient, exceptions
from dotenv import load_dotenv
import os

load_dotenv()
app = Flask(__name__)

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


def get_settings_deepl_secure():
    auth_error = validate_bearer_token(request, 'A7x!G2p@Q9#L')
    if auth_error:
        return auth_error

    admin_id = request.form.get('admin_id')
    if not admin_id:
        return jsonify({"error": "Missing admin_id"}), 400

    try:
        doc = container.read_item(item=admin_id, partition_key=admin_id)
        return jsonify({"admin_id": admin_id, "api_key": doc['api_key']}), 200

    except exceptions.CosmosResourceNotFoundError:
        return jsonify({"error": "No settings found for the given admin_id"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500