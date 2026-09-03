from flask import Flask, request, jsonify
from azure.cosmos import CosmosClient, exceptions
from dotenv import load_dotenv
import os

load_dotenv()
app = Flask(__name__)

cosmos_client = CosmosClient(os.getenv('COSMOS_ENDPOINT'), os.getenv('COSMOS_KEY'))
container = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME')).get_container_client('contextsense_core_prompt')


def validate_bearer_token(request, expected_token):
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({"error": "Invalid or missing Authorization header."}), 401
    token = auth_header.split(' ')[1]
    if token != expected_token:
        return jsonify({"error": "Unauthorized. Invalid Bearer token."}), 403
    return None


@app.route('/delete_core_prompt', methods=['DELETE'])
def delete_core_prompt():
    auth_error = validate_bearer_token(request, 'A7x!G2p@Q9#L')
    if auth_error:
        return auth_error

    try:
        core_prompt_id = request.args.get('core_prompt_id')
        if not core_prompt_id:
            return jsonify({"error": "Missing required parameter: core_prompt_id"}), 400

        core_prompt_id = int(core_prompt_id)

        container.delete_item(item=str(core_prompt_id), partition_key=core_prompt_id)

        return jsonify({
            "message": f"Deleted core_prompt_id {core_prompt_id} successfully"
        }), 200

    except exceptions.CosmosResourceNotFoundError:
        return jsonify({"error": f"No entry found with core_prompt_id {core_prompt_id}"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)