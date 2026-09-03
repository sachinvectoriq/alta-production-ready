import os
from flask import Flask, request, jsonify
from azure.cosmos import CosmosClient
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

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


def delete_row_by_id(row_id):
    query = "SELECT c.id, c.modifier FROM c WHERE c.type = 'alta_filters' AND c.filter_id = @filter_id"
    params = [{"name": "@filter_id", "value": row_id}]
    results = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))

    if not results:
        return False, f"No row found with id {row_id}."

    doc = results[0]
    container.delete_item(item=doc['id'], partition_key=doc['modifier'])
    return True, f"Row with id {row_id} deleted successfully."


def handle_delete_request():
    auth_error = validate_bearer_token(request, 'A7x!G2p@Q9#L')
    if auth_error:
        return auth_error

    row_id = request.args.get('id')

    if not row_id:
        return jsonify({"status": "error", "message": "Missing required query parameter: id"}), 400

    try:
        row_id = int(row_id)
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid id format. Must be an integer."}), 400

    success, message = delete_row_by_id(row_id)

    if success:
        return jsonify({"status": "success", "message": message}), 200
    else:
        return jsonify({"status": "error", "message": message}), 404


if __name__ == "__main__":
    @app.route('/delete', methods=['DELETE'])
    def delete_row():
        return handle_delete_request()

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)