from flask import Flask, request, jsonify, Response
import requests
import time
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
import os
import csv
import io
import logging
from azure.cosmos import CosmosClient, exceptions
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

cosmos_client = CosmosClient(os.getenv('COSMOS_ENDPOINT'), os.getenv('COSMOS_KEY'))
database = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME'))
settings_container = database.get_container_client('settings')
deepl_settings_container = database.get_container_client('deepl_settings')

language_mapping = {
    "Arabic": "AR", "Bulgarian": "BG", "Czech": "CS", "Danish": "DA", "German": "DE",
    "Greek": "EL", "English": "EN", "English (British)": "EN-GB", "English (American)": "EN-US",
    "Spanish": "ES", "Estonian": "ET", "Finnish": "FI", "French": "FR", "Hungarian": "HU",
    "Indonesian": "ID", "Italian": "IT", "Japanese": "JA", "Korean": "KO", "Lithuanian": "LT",
    "Latvian": "LV", "Norwegian Bokmål": "NB", "Dutch": "NL", "Polish": "PL", "Portuguese": "PT",
    "Portuguese (Brazilian)": "PT-BR", "Portuguese (European)": "PT-PT", "Romanian": "RO",
    "Russian": "RU", "Slovak": "SK", "Slovenian": "SL", "Swedish": "SV", "Turkish": "TR",
    "Ukrainian": "UK", "Chinese": "ZH", "Chinese (Simplified)": "ZH-HANS", "Chinese (Traditional)": "ZH-HANT"
}

formality_supported_languages = {"DE", "FR", "IT", "ES", "NL", "PL", "PT-BR", "PT-PT", "JA", "RU"}

DEEPL_API_URL = os.getenv('DEEPL_API_URL')

global storage_connection_string, deepl_api_key
storage_connection_string = None
deepl_api_key = None


def retrieve_settings():
    """
    Fetches storage_connection_string from the settings container and
    api_key from the deepl_settings container -- both point reads against
    admin_id = '1', since each container has admin_id as both its
    partition key and its Cosmos id.
    """
    global storage_connection_string, deepl_api_key

    try:
        settings_doc = settings_container.read_item(item='1', partition_key=1)
        storage_connection_string = settings_doc['storage_connection_string']

        deepl_doc = deepl_settings_container.read_item(item='1', partition_key='1')
        deepl_api_key = deepl_doc['api_key']

        logging.info("Settings retrieved successfully.")
        return deepl_api_key, storage_connection_string

    except exceptions.CosmosResourceNotFoundError as e:
        logging.error(f"Settings not found: {e}")
        return None, None
    except Exception as e:
        logging.error(f"Error retrieving settings: {e}")
        return None, None


def validate_bearer_token(request, expected_token):
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({"error": "Invalid or missing Authorization header."}), 401
    token = auth_header.split(' ')[1]
    if token != expected_token:
        return jsonify({"error": "Unauthorized. Invalid Bearer token."}), 403
    return None


def multiple_files3_secure():
    deepl_api_key, storage_connection_string = retrieve_settings()
    if not deepl_api_key or not storage_connection_string:
        return jsonify({"error": "Failed to retrieve required settings"}), 500
    auth_error = validate_bearer_token(request, 'A7x!G2p@Q9#L')
    if auth_error:
        return auth_error
    try:
        files = request.files.getlist('file')
        source_lang = request.form.get('source_lang', 'auto')
        target_lang = request.form['target_lang']
        formality = request.form['formality']
        glossary_file = request.files.get('glossary_file')

        source_lang_code = language_mapping.get(source_lang, 'auto')
        target_lang_code = language_mapping.get(target_lang)

        glossary_id = None
        if glossary_file:
            try:
                file_content = glossary_file.read().decode('utf-8')
                is_csv = not glossary_file.filename.lower().endswith('.tsv')
                delimiter = ',' if is_csv else '\t'

                rows = list(csv.reader(io.StringIO(file_content), delimiter=delimiter))
                cleaned_rows = []

                for row_idx, row in enumerate(rows):
                    cleaned_row = []
                    for col_idx, cell in enumerate(row):
                        cleaned_cell = cell.strip()
                        cleaned_row.append(cleaned_cell)
                    cleaned_rows.append(cleaned_row)

                output = io.StringIO()
                writer = csv.writer(output, delimiter=delimiter)
                writer.writerows(cleaned_rows)
                cleaned_content = output.getvalue()

                cleaned_file = io.BytesIO(cleaned_content.encode('utf-8'))
                cleaned_file.filename = glossary_file.filename
                cleaned_file.content_type = 'text/csv' if is_csv else 'text/tab-separated-values'

                from create_glossary_deepl2 import upload_glossary
                response = upload_glossary(source_lang, target_lang, cleaned_file)
                if "error" in response:
                    return jsonify({
                        "error": response.get("error"),
                        "status_code": response.get("status_code", 500)
                    }), response.get("status_code", 500)
                print('Response from Upload Glossary:', response)
                glossary_id = response["glossary_id"]

            except Exception as e:
                print(f"Glossary processing error: {str(e)}")
                return jsonify({"error": f"Error processing glossary file: {str(e)}"}), 400

        if not target_lang_code:
            return jsonify({"error": "Invalid target language"}), 400

        if target_lang_code not in formality_supported_languages and formality in ['more', 'less']:
            return jsonify({
                "error": f"Formality '{formality}' is not supported for the target language '{target_lang}'."
            }), 400

        documents_info = []

        for file in files:
            original_filename = file.filename
            file_extension = os.path.splitext(original_filename)[1]
            new_filename = f"{os.path.splitext(original_filename)[0]}-{target_lang_code}{file_extension}"

            file_payload = {
                'file': (new_filename, file.stream, file.content_type),
                'target_lang': (None, target_lang_code),
                'source_lang': (None, source_lang_code if source_lang_code != 'auto' else None),
                'formality': (None, formality)
            }

            if glossary_id:
                file_payload['glossary_id'] = (None, glossary_id)

            headers = {
                'Authorization': f'DeepL-Auth-Key {deepl_api_key}'
            }

            response = requests.post(DEEPL_API_URL, files=file_payload, headers=headers)

            if response.status_code != 200:
                return jsonify({"error": f"File upload failed for {file.filename}"}), response.status_code

            response_data = response.json()
            document_id = response_data['document_id']
            document_key = response_data['document_key']

            translated_blob_name = f"{file.filename.rsplit('.', 1)[0]}-{target_lang_code}.{file.filename.rsplit('.', 1)[-1]}"

            documents_info.append({
                "document_id": document_id,
                "document_key": document_key,
                "file_name": translated_blob_name,
            })

        return jsonify({"documents": documents_info}), 200

    except Exception as e:
        print(f"General error: {str(e)}")
        return jsonify({"error": str(e)}), 500