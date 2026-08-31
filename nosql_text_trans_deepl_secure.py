import deepl
import os
from flask import jsonify, request
import logging
from azure.cosmos import CosmosClient, exceptions
from dotenv import load_dotenv

load_dotenv()

cosmos_client = CosmosClient(os.getenv('COSMOS_ENDPOINT'), os.getenv('COSMOS_KEY'))
database = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME'))
settings_container = database.get_container_client('settings')
deepl_settings_container = database.get_container_client('deepl_settings')

# Language mapping
language_mapping = {
    "Arabic": "AR",
    "Bulgarian": "BG",
    "Czech": "CS",
    "Danish": "DA",
    "German": "DE",
    "Greek": "EL",
    "English": "EN",
    "English (British)": "EN-GB",
    "English (American)": "EN-US",
    "Spanish": "ES",
    "Estonian": "ET",
    "Finnish": "FI",
    "French": "FR",
    "Hungarian": "HU",
    "Indonesian": "ID",
    "Italian": "IT",
    "Japanese": "JA",
    "Korean": "KO",
    "Lithuanian": "LT",
    "Latvian": "LV",
    "Norwegian Bokmål": "NB",
    "Dutch": "NL",
    "Polish": "PL",
    "Portuguese": "PT",
    "Portuguese (Brazilian)": "PT-BR",
    "Portuguese (European)": "PT-PT",
    "Romanian": "RO",
    "Russian": "RU",
    "Slovak": "SK",
    "Slovenian": "SL",
    "Swedish": "SV",
    "Turkish": "TR",
    "Ukrainian": "UK",
    "Chinese": "ZH",
    "Chinese (Simplified)": "ZH-HANS",
    "Chinese (Traditional)": "ZH-HANT"
}

formality_supported_languages = {"DE", "FR", "IT", "ES", "NL", "PL", "PT-BR", "PT-PT", "JA", "RU"}


global DEEPL_API_KEY, storage_connection_string2
DEEPL_API_KEY = None
storage_connection_string2 = None


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


def validate_bearer_token(request, expected_token):
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({"error": "Invalid or missing Authorization header."}), 401
    token = auth_header.split(' ')[1]
    if token != expected_token:
        return jsonify({"error": "Unauthorized. Invalid Bearer token."}), 403
    return None


def translate_text(text, target_lang_name, source_lang_name=None, formality='default', preserve_formatting=True):
    """Performs the translation using DeepL API."""
    if not text or not target_lang_name:
        raise ValueError("Missing required parameters: 'text' and 'target_lang'.")

    DEEPL_API_KEY, storage_connection_string2 = retrieve_settings()
    if not DEEPL_API_KEY or not storage_connection_string2:
        return jsonify({"error": "Failed to retrieve required settings"}), 500
    translator = deepl.Translator(DEEPL_API_KEY)

    source_lang = language_mapping.get(source_lang_name) if source_lang_name else None
    target_lang = language_mapping.get(target_lang_name)

    if target_lang is None:
        raise ValueError(f"Invalid target language: '{target_lang_name}'. Please provide a valid language name.")
    try:
        result = translator.translate_text(
            text,
            source_lang=source_lang,
            target_lang=target_lang,
            formality=formality,
            preserve_formatting=True
        )
        return result.text
    except Exception as e:
        raise RuntimeError(f"Translation failed: {str(e)}")


def handle_translation_request_secure(data):

    auth_error = validate_bearer_token(request, 'A7x!G2p@Q9#L')
    if auth_error:
        return auth_error

    """Handles the translation request and returns the appropriate response."""
    text = data.get('text')
    target_language = data.get('target_language')
    source_language = data.get('source_language', None)

    if not text or not target_language:
        return jsonify({'error': 'Please provide text and target_language'}), 400

    formality = data.get('formality', 'default')

    try:
        translated_text = translate_text(text, target_language, source_language, formality)
        return jsonify({'translated_text': translated_text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500