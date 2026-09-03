from flask import Flask, request, jsonify
import requests
import os
from azure.cosmos import CosmosClient, exceptions
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

cosmos_client = CosmosClient(os.getenv('COSMOS_ENDPOINT'), os.getenv('COSMOS_KEY'))
database = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME'))
settings_container = database.get_container_client('settings')
deepl_settings_container = database.get_container_client('deepl_settings')

DEEPL_BASE_URL = os.getenv('DEEPL_API_URL')

global storage_connection_string, deepl_api_key
deepl_api_key = None
storage_connection_string = None


def retrieve_settings():
    """
    Retrieves DeepL API key and Azure Storage connection string --
    settings from settings container, api_key from deepl_settings container.
    """
    global storage_connection_string, deepl_api_key
    user_name = request.args.get('user_name')

    try:
        settings_doc = settings_container.read_item(item='1', partition_key=1)
        storage_connection_string = settings_doc['storage_connection_string']

        deepl_doc = deepl_settings_container.read_item(item='1', partition_key='1')
        deepl_api_key = deepl_doc['api_key']

        return deepl_api_key, storage_connection_string

    except exceptions.CosmosResourceNotFoundError:
        return None, None
    except Exception as e:
        return None, None


def validate_bearer_token(request, expected_token):
    user_name = request.args.get('user_name')
    auth_header = request.headers.get('Authorization', '')

    if not auth_header.startswith('Bearer '):
        return jsonify({"error": "Invalid or missing Authorization header."}), 401

    token = auth_header.split(' ')[1]
    if token != expected_token:
        return jsonify({"error": "Unauthorized. Invalid Bearer token."}), 403

    return None


def check_status_secure():
    """
    Checks the translation status of documents with DeepL API.
    """
    user_name = request.args.get('user_name')

    deepl_api_key, storage_connection_string = retrieve_settings()
    if not deepl_api_key or not storage_connection_string:
        return jsonify({"error": "Failed to retrieve required settings"}), 500

    auth_error = validate_bearer_token(request, 'A7x!G2p@Q9#L')
    if auth_error:
        return auth_error

    try:
        input_data = request.json

        if not isinstance(input_data, list) or len(input_data) == 0:
            return jsonify(
                {'error': 'Input should be a list of dictionaries with file_name, document_id, and document_key'}), 400

        results = []

        for group in input_data:
            file_name = group.get('file_name')
            document_id = group.get('document_id')
            document_key = group.get('document_key')

            if not file_name or not document_id or not document_key:
                results.append({
                    'file_name': file_name or 'Unknown',
                    'error': 'Missing document_id or document_key'
                })
                continue

            url = f"{DEEPL_BASE_URL}/{document_id}"
            headers = {'Authorization': f"DeepL-Auth-Key {deepl_api_key}"}
            params = {'document_key': document_key}

            try:
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                response_data = response.json()

                if response.status_code == 200:
                    if response_data.get('status') == 'error':
                        results.append({
                            'file_name': file_name,
                            'document_id': document_id,
                            'document_key': document_key,
                            'status': 'error',
                            'error': response_data.get('message', 'No message')
                        })
                    else:
                        results.append({
                            'file_name': file_name,
                            'document_id': document_id,
                            'document_key': document_key,
                            'status': response_data.get('status'),
                            'seconds_remaining': response_data.get('seconds_remaining'),
                            'billed_characters': response_data.get('billed_characters')
                        })

                else:
                    results.append({
                        'file_name': file_name,
                        'error': response_data.get('message', 'Unknown error')
                    })
            except requests.exceptions.HTTPError as http_err:
                results.append({
                    'file_name': file_name,
                    'error': f"DeepL API HTTP error: {http_err}. Message: {response.json().get('message', 'No message')}"
                })
            except requests.exceptions.ConnectionError as conn_err:
                results.append({
                    'file_name': file_name,
                    'error': f"Network connection error to DeepL API: {conn_err}"
                })
            except requests.exceptions.Timeout as timeout_err:
                results.append({
                    'file_name': file_name,
                    'error': f"DeepL API request timed out: {timeout_err}"
                })
            except requests.exceptions.RequestException as req_err:
                results.append({
                    'file_name': file_name,
                    'error': f"An unexpected request error: {req_err}"
                })
            except Exception as e:
                results.append({
                    'file_name': file_name,
                    'error': f"Error checking status: {str(e)}"
                })

        overall_code = 200
        for r in results:
            if r.get('status') == 'error':
                overall_code = 207
                break

        return jsonify(results), overall_code

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))