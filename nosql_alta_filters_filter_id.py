from flask import Flask, request, jsonify
from azure.cosmos import CosmosClient
from dotenv import load_dotenv
import os

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


def get_alta_filter_by_id(filter_id):
    query = "SELECT * FROM c WHERE c.type = 'alta_filters' AND c.filter_id = @filter_id"
    params = [{"name": "@filter_id", "value": filter_id}]
    results = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))

    if not results:
        return None, "No record found with the specified ID"

    doc = results[0]
    result_dict = {
        "id": doc["filter_id"],
        "modifier": doc["modifier"],
        "value": doc["value"],
        "system_prompt": doc["system_prompt"],
        "user_prompt": doc["user_prompt"],
        "created_by": doc["created_by"],
        "created_at": doc["created_at"],
        "updated_at": doc["updated_at"],
        "sequence": doc["sequence"],
        "status": doc["status"]
    }
    return result_dict, None


@app.route('/alta_filters/id', methods=['GET'])
def get_filter():
    auth_error = validate_bearer_token(request, 'A7x!G2p@Q9#L')
    if auth_error:
        return auth_error

    filter_id = request.args.get('id')

    if not filter_id:
        return jsonify({"status": "error", "message": "Missing required query parameter: id"}), 400

    try:
        filter_id = int(filter_id)
    except ValueError:
        return jsonify({"status": "error", "message": "ID must be an integer"}), 400

    result, error = get_alta_filter_by_id(filter_id)

    if error:
        return jsonify({"status": "error", "message": error}), 404

    return jsonify({"status": "success", "data": result}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)