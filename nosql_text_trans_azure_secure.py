from flask import Flask, request, jsonify
import logging
import requests
import json
from urllib.parse import urlencode
import uuid
from azure.cosmos import CosmosClient, exceptions
from dotenv import load_dotenv
import os

load_dotenv()
app = Flask(__name__)

cosmos_client = CosmosClient(os.getenv('COSMOS_ENDPOINT'), os.getenv('COSMOS_KEY'))
settings_container = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME')).get_container_client('settings')


def validate_bearer_token(request, expected_token):
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({"error": "Invalid or missing Authorization header."}), 401
    token = auth_header.split(' ')[1]
    if token != expected_token:
        return jsonify({"error": "Unauthorized. Invalid Bearer token."}), 403
    return None


def get_supported_languages(endpoint, api_key):
    try:
        url = f"{endpoint.rstrip('/')}/languages?api-version=3.0"
        headers = {
            'Ocp-Apim-Subscription-Key': api_key,
            'Content-Type': 'application/json'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to retrieve supported languages: {str(e)}")
        raise e


def get_language_code(language_name, supported_languages):
    if supported_languages['translation'] is not None:
        for key, value in supported_languages['translation'].items():
            if value['name'].lower() == language_name.lower() or value['nativeName'].lower() == language_name.lower():
                return key
    return None


def fetch_settings(admin_id):
    """
    Point-read against the settings container -- admin_id is the partition
    key and also the document's Cosmos id, so this is a single, direct
    lookup with no query needed (same shape as the original single-row
    SELECT ... WHERE admin_id = %s).
    """
    try:
        admin_id_int = int(admin_id)
        doc = settings_container.read_item(item=str(admin_id_int), partition_key=admin_id_int)
        return (doc['key'], doc['text_translation_endpoint'], doc['region'])
    except exceptions.CosmosResourceNotFoundError:
        return None
    except Exception as e:
        logging.error(f"Database error occurred: {e}", exc_info=True)
        return None


@app.route('/text_trans_azure_secure', methods=['POST'])
def text_trans_azure_secure():
    logging.info('Processing translation request.')

    auth_error = validate_bearer_token(request, 'A7x!G2p@Q9#L')
    if auth_error:
        return auth_error

    admin_id = '1'

    result = fetch_settings(admin_id)

    if result is None or len(result) < 3:
        logging.error("Failed to retrieve all required settings (key, text_translation_endpoint, region).")
        return jsonify({"error": "Failed to retrieve all required settings (key, text_translation_endpoint, region)."}), 500

    key, text_translation_endpoint, region = result

    data = request.get_json()
    target_language_name = data.get('target_language')
    source_language_name = data.get('source_language')
    text_to_translate = data.get('text')

    if target_language_name and text_to_translate:
        supported_languages = get_supported_languages(text_translation_endpoint, key)

        target_language_code = get_language_code(target_language_name, supported_languages)
        if not target_language_code:
            return jsonify({"error": f"Target language '{target_language_name}' is not supported."}), 400

        source_language_code = None
        if source_language_name:
            source_language_code = get_language_code(source_language_name, supported_languages)
            if not source_language_code:
                return jsonify({"error": f"Source language '{source_language_name}' is not supported."}), 400

        path = '/translate'
        constructed_url = f"{text_translation_endpoint.rstrip('/')}{path}"

        params = {
            'api-version': '3.0',
            'to': [target_language_code]
        }

        if source_language_code:
            params['from'] = source_language_code

        headers = {
            'Ocp-Apim-Subscription-Key': key,
            'Ocp-Apim-Subscription-Region': region,
            'Content-type': 'application/json',
            'X-ClientTraceId': str(uuid.uuid4())
        }

        body = [{'text': text_to_translate}]

        try:
            response = requests.post(constructed_url, params=params, headers=headers, json=body)
            response.raise_for_status()
            billed_characters = response.headers.get("X-metered-usage")
            response_json = response.json()

            return jsonify({
                "translation": response_json,
                "billed_characters": int(billed_characters) if billed_characters else None
            }), 200

        except requests.exceptions.HTTPError as http_err:
            logging.error(f"HTTP error occurred: {http_err}", exc_info=True)
            return jsonify({"error": f"HTTP error occurred: {http_err}"}), 500
        except requests.exceptions.RequestException as req_err:
            logging.error(f"Request error occurred: {req_err}", exc_info=True)
            return jsonify({"error": f"Request error occurred: {req_err}"}), 500
    else:
        return jsonify({"error": "Please pass target_language and text in the request."}), 400


if __name__ == '__main__':
    app.run(debug=True)