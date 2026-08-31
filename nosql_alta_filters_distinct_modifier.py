from azure.cosmos import CosmosClient
from dotenv import load_dotenv
from flask import request, jsonify
import os

load_dotenv()

cosmos_client = CosmosClient(os.getenv('COSMOS_ENDPOINT'), os.getenv('COSMOS_KEY'))
container = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME')).get_container_client('alta_filters')


def validate_bearer_token(request, expected_token):
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({"error": "Invalid or missing Authorization header."}), 401
    token = auth_header.split(' ')[1]
    if token != expected_token:
        return jsonify({"error": "Unauthorized. Invalid Bearer token."}), 403
    return None


def get_distinct_modifiers():
    auth_error = validate_bearer_token(request, 'A7x!G2p@Q9#L')
    if auth_error:
        return auth_error

    try:
        query = "SELECT DISTINCT VALUE c.modifier FROM c WHERE c.type = 'alta_filters'"
        modifiers = list(container.query_items(query=query, enable_cross_partition_query=True))
        return modifiers
    except Exception as e:
        print(f"Error: {e}")
        return None