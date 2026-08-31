from flask import request, jsonify
from azure.cosmos import CosmosClient, exceptions
from dotenv import load_dotenv
import os

load_dotenv()

cosmos_client = CosmosClient(os.getenv('COSMOS_ENDPOINT'), os.getenv('COSMOS_KEY'))
container = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME')).get_container_client('settings')


def validate_bearer_token(request, expected_token):
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({"error": "Invalid or missing Authorization header."}), 401
    token = auth_header.split(' ')[1]
    if token != expected_token:
        return jsonify({"error": "Unauthorized. Invalid Bearer token."}), 403
    return None


def retrieve_settings_secure():
    auth_error = validate_bearer_token(request, 'A7x!G2p@Q9#L')
    if auth_error:
        return auth_error

    try:
        admin_id = request.args.get('admin_id')

        if not admin_id:
            return jsonify({"error": "Please provide an 'admin_id'."}), 400

        try:
            admin_id_int = int(admin_id)
        except ValueError:
            return jsonify({"error": "admin_id must be an integer."}), 400

        try:
            doc = container.read_item(item=str(admin_id_int), partition_key=admin_id_int)
        except exceptions.CosmosResourceNotFoundError:
            return jsonify({"error": f"No settings found for Admin_id {admin_id}."}), 404

        settings = {
            'key': doc['key'],
            'text_translation_endpoint': doc['text_translation_endpoint'],
            'document_translation_endpoint': doc['document_translation_endpoint'],
            'region': doc['region'],
            'storage_connection_string': doc['storage_connection_string']
        }

        return jsonify(settings), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "An error occurred while retrieving the settings."}), 500