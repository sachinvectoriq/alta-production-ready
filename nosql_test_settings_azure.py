# test_settings_azure.py

import os
import requests
from flask import request, jsonify
from azure.storage.blob import BlobServiceClient
import traceback

# Import log and flush from the Cosmos-backed logging_config
from logging_config import log, flush

SOURCE_DOCUMENT_URL = os.getenv("SOURCE_DOCUMENT_URL")
TARGET_DOCUMENT_URL = os.getenv("TARGET_DOCUMENT_URL")
SOURCE_LANGUAGE_CODE = "en"
TARGET_LANGUAGE_CODE = "es"


def test_translation():
    log('INFO', 'Received request to test Azure Text Translation.')
    key = request.form.get('key')
    text_translation_endpoint = request.form.get('endpoint')
    region = request.form.get('region')

    source_language_code = "en"
    target_language_code = "es"
    text_to_translate = "This is a test"

    if not key or not text_translation_endpoint or not region:
        log('WARNING', 'Missing required parameters for text translation test.',
            data={'key_provided': bool(key), 'endpoint_provided': bool(text_translation_endpoint),
                  'region_provided': bool(region)})
        flush()
        return jsonify({"error": "API key, endpoint, and region are required."}), 400

    log('INFO', 'All required parameters for text translation test are present.')

    path = 'translate'
    constructed_url = f"{text_translation_endpoint}/{path}"

    params = {
        'api-version': '3.0',
        'from': source_language_code,
        'to': target_language_code
    }

    headers = {
        'Ocp-Apim-Subscription-Key': key,
        'Ocp-Apim-Subscription-Region': region,
        'Content-Type': 'application/json'
    }

    body = [{'text': text_to_translate}]

    try:
        log('INFO', 'Making request to Azure Text Translator API.',
            data={'url': constructed_url, 'from': source_language_code, 'to': target_language_code})
        response = requests.post(constructed_url, params=params, headers=headers, json=body)
        response.raise_for_status()

        response_json = response.json()
        log('INFO', 'Azure Text Translator API call successful.',
            data={'status_code': response.status_code, 'response_preview': str(response_json)[:200]})
        flush()
        return jsonify(response_json), 200

    except requests.exceptions.HTTPError as http_err:
        error_traceback = traceback.format_exc()
        log('ERROR', f"HTTP error occurred during text translation: {http_err}",
            data={'status_code': http_err.response.status_code if http_err.response else 'N/A',
                  'response_text': http_err.response.text if http_err.response else 'N/A',
                  'traceback': error_traceback})
        flush()
        return jsonify({"error": f"HTTP error occurred: {http_err}"}), 500
    except Exception as e:
        error_traceback = traceback.format_exc()
        log('CRITICAL', f"An unexpected error occurred during text translation: {e}",
            data={'traceback': error_traceback})
        flush()
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


def translate_document():
    log('INFO', 'Received request to test Azure Document Translation.')
    key = request.form.get('key')
    text_translation_endpoint = request.form.get('endpoint')
    region = request.form.get('region')

    if not key or not text_translation_endpoint or not region:
        log('WARNING', 'Missing required parameters for document translation test.',
            data={'key_provided': bool(key), 'endpoint_provided': bool(text_translation_endpoint),
                  'region_provided': bool(region)})
        flush()
        return jsonify({"error": "API key, endpoint, and region are required."}), 400

    log('INFO', 'All required parameters for document translation test are present.')

    constructed_url = f"{text_translation_endpoint}/translator/text/batch/v1.0/batches"

    body = {
        "inputs": [
            {
                "source": {
                    "sourceUrl": SOURCE_DOCUMENT_URL,
                    "language": SOURCE_LANGUAGE_CODE
                },
                "targets": [
                    {
                        "targetUrl": TARGET_DOCUMENT_URL,
                        "language": TARGET_LANGUAGE_CODE
                    }
                ]
            }
        ]
    }

    headers = {
        'Ocp-Apim-Subscription-Key': key,
        'Ocp-Apim-Subscription-Region': region,
        'Content-Type': 'application/json'
    }

    try:
        log('INFO', 'Making request to Azure Document Translation API.',
            data={'url': constructed_url, 'source_doc_url': SOURCE_DOCUMENT_URL, 'target_doc_url': TARGET_DOCUMENT_URL})
        response = requests.post(constructed_url, headers=headers, json=body)

        log('INFO', f"Document Translation API Response - Status Code: {response.status_code}",
            data={'response_text_preview': response.text[:200]})

        response.raise_for_status()

        log('INFO', "Document translation request sent successfully to Azure.")
        flush()
        return jsonify({"success": True, "message": "Document translation started successfully."}), 200

    except requests.exceptions.HTTPError as http_err:
        error_traceback = traceback.format_exc()
        log('ERROR', f"HTTP error occurred during document translation: {http_err}",
            data={'status_code': http_err.response.status_code if http_err.response else 'N/A',
                  'response_text': http_err.response.text if http_err.response else 'N/A',
                  'traceback': error_traceback})
        flush()
        return jsonify({"error": f"HTTP error occurred: {http_err}"}), 500
    except Exception as e:
        error_traceback = traceback.format_exc()
        log('CRITICAL', f"An unexpected error occurred during document translation: {e}",
            data={'traceback': error_traceback})
        flush()
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


def validate_connection_string(connection_string):
    log('INFO', 'Attempting to validate Azure Blob Storage connection string.')
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        log('INFO', 'Attempting to list containers to validate Azure Blob Storage connection.')
        containers = blob_service_client.list_containers()
        for container in containers:
            pass
        log('INFO', 'Azure Blob Storage connection string validated successfully.')
        return True
    except Exception as e:
        error_traceback = traceback.format_exc()
        log('ERROR', f"Connection string validation failed: {e}",
            data={'error_details': str(e), 'traceback': error_traceback})
        return False


def validate_connection_string_route():
    log('INFO', 'Received request to validate Azure Blob Storage connection string via route.')
    connection_string = request.form.get('connection_string')

    if not connection_string:
        log('WARNING', 'Connection string is missing for validation route.')
        flush()
        return jsonify({"error": "Connection string is required."}), 400

    if validate_connection_string(connection_string):
        log('INFO', 'Azure Blob Storage connection string is valid.')
        flush()
        return jsonify({"success": True, "message": "Valid Azure Blob Storage connection string."}), 200
    else:
        log('ERROR', 'Azure Blob Storage connection string is invalid.')
        flush()
        return jsonify({"error": "Invalid Azure Blob Storage connection string."}), 400


def run_all_operations():
    log('INFO',
        'Received request to run all Azure operations (Text, Document Translation, and Blob Storage validation).')
    key = request.form.get('key')
    text_translation_endpoint = request.form.get('text_translation_endpoint')
    document_translation_endpoint = request.form.get('document_translation_endpoint')
    region = request.form.get('region')

    if not key or not text_translation_endpoint or not document_translation_endpoint or not region:
        log('WARNING', 'Missing one or more required parameters for running all operations.',
            data={'key_provided': bool(key), 'text_endpoint_provided': bool(text_translation_endpoint),
                  'doc_endpoint_provided': bool(document_translation_endpoint), 'region_provided': bool(region)})
        flush()
        return jsonify({
            "error": "API key, text translation endpoint, document translation endpoint, and region are required."
        }), 400

    log('INFO', 'All required parameters for running all operations are present.')

    results = {}
    all_successful = True

    log('INFO', 'Starting Text Translation test within run_all_operations.')
    try:
        source_language_code = "en"
        target_language_code = "es"
        text_to_translate = "This is a test"

        constructed_url = f"{text_translation_endpoint}/translate"
        params = {'api-version': '3.0', 'from': source_language_code, 'to': target_language_code}
        headers = {
            'Ocp-Apim-Subscription-Key': key,
            'Ocp-Apim-Subscription-Region': region,
            'Content-Type': 'application/json'
        }
        body = [{'text': text_to_translate}]

        translation_response = requests.post(constructed_url, params=params, headers=headers, json=body)
        translation_response.raise_for_status()

        results['text_translation'] = translation_response.json()
        log('INFO', 'Text Translation test successful in run_all_operations.')
    except Exception as e:
        error_traceback = traceback.format_exc()
        results['text_translation'] = {"error": str(e), "traceback": error_traceback}
        all_successful = False
        log('ERROR', f'Text Translation test failed in run_all_operations: {e}', data={'traceback': error_traceback})

    log('INFO', 'Starting Document Translation test within run_all_operations.')
    try:
        document_translation_url = f"{document_translation_endpoint}/translator/text/batch/v1.0/batches"
        body = {
            "inputs": [
                {
                    "source": {"sourceUrl": SOURCE_DOCUMENT_URL, "language": SOURCE_LANGUAGE_CODE},
                    "targets": [{"targetUrl": TARGET_DOCUMENT_URL, "language": TARGET_LANGUAGE_CODE}]
                }
            ]
        }
        headers = {
            'Ocp-Apim-Subscription-Key': key,
            'Ocp-Apim-Subscription-Region': region,
            'Content-Type': 'application/json'
        }

        document_response = requests.post(document_translation_url, headers=headers, json=body)
        document_response.raise_for_status()

        results['document_translation'] = {"message": "Document translation started successfully."}
        log('INFO', 'Document Translation test successful in run_all_operations.')
    except Exception as e:
        error_traceback = traceback.format_exc()
        results['document_translation'] = {"error": str(e), "traceback": error_traceback}
        all_successful = False
        log('ERROR', f'Document Translation test failed in run_all_operations: {e}',
            data={'traceback': error_traceback})

    if all_successful:
        log('INFO', 'All Azure operations completed successfully.')
        flush()
        return jsonify(results), 200
    else:
        log('ERROR', 'One or more Azure operations failed during run_all_operations.', data={'results': results})
        flush()
        return jsonify(results), 500