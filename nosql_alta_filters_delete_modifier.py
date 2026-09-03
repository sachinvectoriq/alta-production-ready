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


@app.route('/delete_filter', methods=['DELETE'])
def delete_modifier():
    auth_error = validate_bearer_token(request, 'A7x!G2p@Q9#L')
    if auth_error:
        return auth_error

    try:
        modifier = request.args.get('modifier')
        if not modifier:
            return jsonify({"error": "Missing required parameter: modifier"}), 400

        # Single-partition query — efficient, since modifier IS the partition key
        query = "SELECT c.id, c.filter_id FROM c WHERE c.type = 'alta_filters' AND c.modifier = @modifier"
        params = [{"name": "@modifier", "value": modifier}]
        items = list(container.query_items(query=query, parameters=params, partition_key=modifier))

        if not items:
            return jsonify({"error": f"No filters found with modifier '{modifier}'"}), 404

        deleted_ids = []
        for item in items:
            container.delete_item(item=item['id'], partition_key=modifier)
            deleted_ids.append(item['filter_id'])

        return jsonify({
            "message": f"Deleted {len(deleted_ids)} filters with modifier '{modifier}'",
            "deleted_ids": deleted_ids
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)