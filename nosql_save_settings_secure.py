from azure.cosmos import CosmosClient
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import os

load_dotenv()
app = Flask(__name__)

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


@app.route('/save_settings_secure', methods=['POST'])
def save_settings_secure():
    auth_error = validate_bearer_token(request, 'A7x!G2p@Q9#L')
    if auth_error:
        return auth_error

    try:
        admin_id = 1  # hardcoded, preserved exactly as in the original

        key = request.form.get('key')
        text_translation_endpoint = request.form.get('text_translation_endpoint')
        document_translation_endpoint = request.form.get('document_translation_endpoint')
        region = request.form.get('region')
        storage_connection_string = request.form.get('storage_connection_string')

        if not (key and text_translation_endpoint and document_translation_endpoint and region and storage_connection_string):
            return jsonify({"error": "Missing one or more required parameters."}), 400

        item = {
            "id": str(admin_id),
            "type": "settings",
            "admin_id": admin_id,
            "key": key,
            "text_translation_endpoint": text_translation_endpoint,
            "document_translation_endpoint": document_translation_endpoint,
            "region": region,
            "storage_connection_string": storage_connection_string
        }

        # upsert_item natively replicates INSERT ... ON CONFLICT DO UPDATE:
        # creates the item if id+partition key don't exist, replaces it if they do.
        container.upsert_item(body=item)

        return jsonify({"message": f"Settings for Admin_id {admin_id} saved successfully."}), 200

    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({"error": "An unexpected error occurred while saving the settings."}), 500


if __name__ == '__main__':
    app.run(debug=True)