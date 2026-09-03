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


@app.route('/update_prompt', methods=['PUT'])
def update_prompt():
    auth_error = validate_bearer_token(request, 'A7x!G2p@Q9#L')
    if auth_error:
        return auth_error

    core_prompt_id = request.args.get('core_prompt_id')
    prompt = request.args.get('prompt')

    if not core_prompt_id or not prompt:
        return jsonify({"error": "Missing core_prompt_id or prompt parameter"}), 400

    try:
        core_prompt_id = int(core_prompt_id)

        doc = container.read_item(item=str(core_prompt_id), partition_key=core_prompt_id)
        doc['prompt'] = prompt
        container.replace_item(item=doc['id'], body=doc)

        return jsonify({
            "message": "Prompt updated successfully",
            "data": {"core_prompt_id": doc["core_prompt_id"], "prompt": doc["prompt"]}
        }), 200

    except exceptions.CosmosResourceNotFoundError:
        return jsonify({"error": "core_prompt_id not found"}), 404
    except ValueError:
        return jsonify({"error": "Invalid core_prompt_id. It must be an integer."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)