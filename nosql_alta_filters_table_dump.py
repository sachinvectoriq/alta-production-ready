from flask import Flask, jsonify, request
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


@app.route('/get_grouped_filters', methods=['GET'])
def get_grouped_filters():
    auth_error = validate_bearer_token(request, 'A7x!G2p@Q9#L')
    if auth_error:
        return auth_error

    try:
        query = "SELECT * FROM c WHERE c.type = 'alta_filters'"
        data = list(container.query_items(query=query, enable_cross_partition_query=True))

        grouped_data = {}
        for item in data:
            modifier = item["modifier"]
            if modifier not in grouped_data:
                grouped_data[modifier] = {
                    "modifier": modifier,
                    "sequence": item["sequence"],
                    "status": item["status"],
                    "values": []
                }
            grouped_data[modifier]["values"].append({
                "id": item["filter_id"],
                "modifier": item["modifier"],
                "value": item["value"],
                "system": item["system_prompt"],
                "user": item["user_prompt"]
            })

        return jsonify(list(grouped_data.values()))

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)