from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
import requests
from flask import Flask, request, jsonify
import os
import re
import random
import logging
from azure.cosmos import CosmosClient, exceptions
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

cosmos_client = CosmosClient(os.getenv('COSMOS_ENDPOINT'), os.getenv('COSMOS_KEY'))
database = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME'))
settings_container = database.get_container_client('settings')
deepl_settings_container = database.get_container_client('deepl_settings')

global DEEPL_API_KEY, account_key, STORAGE_ACCOUNT_NAME, connection_string, admin_id, storage_connnection_string2

storage_connection_string2 = None
DEEPL_API_KEY = None
account_key = None
STORAGE_ACCOUNT_NAME = None
sas_urls = []
connection_string = None

DEEPL_API_URL = os.getenv('DEEPL_DOCUMENT_TRANSLATION_URL')

admin_id = 1


def retrieve_settings():
    global storage_connection_string2, DEEPL_API_KEY

    try:
        settings_doc = settings_container.read_item(item='1', partition_key=1)
        storage_connection_string2 = settings_doc['storage_connection_string']

        deepl_doc = deepl_settings_container.read_item(item='1', partition_key='1')
        DEEPL_API_KEY = deepl_doc['api_key']

        logging.info("Settings retrieved successfully.")
        return DEEPL_API_KEY, storage_connection_string2

    except exceptions.CosmosResourceNotFoundError as e:
        logging.error(f"Settings not found: {e}")
        return None, None
    except Exception as e:
        logging.error(f"Error retrieving settings: {e}")
        return None, None


def get_settings():
    global connection_string, api_key, endpoint, document_translation_endpoint, blob_service_client, base_path
    try:
        doc = settings_container.read_item(item=str(admin_id), partition_key=admin_id)

        api_key = doc['key']
        endpoint = doc['text_translation_endpoint']
        document_translation_endpoint = doc['document_translation_endpoint']
        region = doc['region']
        connection_string = doc['storage_connection_string']
        base_path = f"{document_translation_endpoint}/translator/document/batches"

        if not all([connection_string, api_key, endpoint, document_translation_endpoint, base_path]):
            logging.error("Missing required settings.")
            return False

        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        logging.info("Settings retrieved and blob client initialized.")
        return True

    except exceptions.CosmosResourceNotFoundError:
        logging.error("No settings found for the specified admin_id.")
        return False
    except Exception as e:
        logging.error(f"Database error: {e}")
        return False


def parse_storage_account_details():
    global STORAGE_ACCOUNT_NAME, account_key, connection_string
    try:
        account_name_start = connection_string.find("AccountName=") + len("AccountName=")
        account_name_end = connection_string.find(";", account_name_start)
        account_key_start = connection_string.find("AccountKey=") + len("AccountKey=")
        account_key_end = connection_string.find(";", account_key_start)

        STORAGE_ACCOUNT_NAME = connection_string[account_name_start:account_name_end]
        account_key = connection_string[account_key_start:account_key_end]

        logging.info(f"Storage account name extracted: {STORAGE_ACCOUNT_NAME}")
        logging.info("Storage account key extracted.")
    except Exception as ex:
        logging.error(f"Failed to parse storage account details: {ex}")


def validate_bearer_token(request, expected_token):
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({"error": "Invalid or missing Authorization header."}), 401
    token = auth_header.split(' ')[1]
    if token != expected_token:
        return jsonify({"error": "Unauthorized. Invalid Bearer token."}), 403
    return None


@app.route('/download_translate_upload', methods=['POST'])
def download_translate_upload_secure():

    DEEPL_API_KEY, storage_connection_string2 = retrieve_settings()
    if not DEEPL_API_KEY or not storage_connection_string2:
        return jsonify({"error": "Failed to retrieve DEEPL_API_KEY"}), 500
    print(DEEPL_API_KEY)

    if not get_settings():
        return jsonify({"message": "Failed to retrieve settings."}), 500

    parse_storage_account_details()

    auth_error = validate_bearer_token(request, 'A7x!G2p@Q9#L')
    if auth_error:
        return auth_error

    try:
        document_id = request.form.get("document_id")
        document_key = request.form.get("document_key")
        translated_blob_name = request.form.get("file_name")

        if not document_id or not document_key:
            return jsonify({"error": "Both document_id and document_key are required."}), 400

        headers = {'Authorization': f'DeepL-Auth-Key {DEEPL_API_KEY}'}
        download_response = requests.post(
            f"{DEEPL_API_URL}/{document_id}/result",
            json={"document_key": document_key},
            headers=headers
        )

        if download_response.status_code != 200:
            return jsonify({"error": f"Failed to download translated file: {download_response.text}"}), download_response.status_code

        blob_service_client = BlobServiceClient.from_connection_string(connection_string)

        container_name = os.getenv('DEEPL_CONTAINER')

        blob_client = blob_service_client.get_blob_client(container=container_name, blob=translated_blob_name)

        if blob_client.exists():
            random_number = random.randint(100, 999)
            translated_blob_name = f"{translated_blob_name.rsplit('.', 1)[0]}-{random_number}.{translated_blob_name.rsplit('.', 1)[-1]}"
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=translated_blob_name)

        blob_client.upload_blob(download_response.content, overwrite=True)

        sas_token = generate_blob_sas(
            account_name=STORAGE_ACCOUNT_NAME,
            account_key=account_key,
            container_name=container_name,
            blob_name=translated_blob_name,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=1)
        )

        sas_url = f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net/{container_name}/{translated_blob_name}?{sas_token}"
        sas_urls.append({"file_name": translated_blob_name, "sas_url": sas_url})

        sas_data = []
        sas_data.append({
            "file_name": translated_blob_name,
            "sas_url": sas_url,
        })

        return jsonify({"sas_data": sas_data, "Status": "Succeded"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)