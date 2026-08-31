from flask import Flask, jsonify
from azure.cosmos import CosmosClient, exceptions
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

cosmos_client = CosmosClient(os.getenv('COSMOS_ENDPOINT'), os.getenv('COSMOS_KEY'))
database = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME'))
container = database.get_container_client('alta_var_settings')


def nosql_get_token_limit():
    try:
        # query = "SELECT c.value FROM c WHERE c.type = 'alta_var_settings' AND c.key = 'token_limit'"
        query = """
            SELECT c["value"]
            FROM c
            WHERE c["type"] = "alta_var_settings"
            AND c["key"] = "token_limit"
        """
        results = list(container.query_items(query=query, partition_key='token_limit'))

        if not results:
            return jsonify({
                "error": "token_limit not found in database"
            }), 404

        token_limit_str = results[0]['value']

        try:
            token_limit = int(token_limit_str)
        except ValueError:
            return jsonify({
                "error": "token_limit is not a valid integer",
                "raw_value": token_limit_str
            }), 500

        return jsonify({
            "token_limit": token_limit
        }), 200

    except exceptions.CosmosHttpResponseError as e:
        return jsonify({
            "error": f"Database error: {e.message}"
        }), 500
    except Exception as e:
        return jsonify({
            "error": f"Unexpected error: {str(e)}"
        }), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)