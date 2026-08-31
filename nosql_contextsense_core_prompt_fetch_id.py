from flask import Flask, request, jsonify
from azure.cosmos import CosmosClient, exceptions
from dotenv import load_dotenv
from datetime import datetime, timezone
from typing import Any
import uuid
import os

load_dotenv()
app = Flask(__name__)

cosmos_client = CosmosClient(os.getenv('COSMOS_ENDPOINT'), os.getenv('COSMOS_KEY'))
database = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME'))
container = database.get_container_client('contextsense_core_prompt')
logs_container = database.get_container_client('logs')


def validate_bearer_token(request, expected_token):
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({"error": "Invalid or missing Authorization header."}), 401
    token = auth_header.split(' ')[1]
    if token != expected_token:
        return jsonify({"error": "Unauthorized. Invalid Bearer token."}), 403
    return None


def log_message(connection, level: str, message: str, log_data: dict[str, Any] | None = None, session_id: str | None = None) -> None:
    """
    Logs a message to the logs container.
    'connection' kept as a parameter only for compatibility with existing
    call sites in this file -- Cosmos doesn't need a connection object.
    """
    now = datetime.now(timezone.utc)
    log_id = int(now.timestamp() * 1_000_000)

    item = {
        "id": str(uuid.uuid4()),
        "type": "logs",
        "log_id": log_id,
        "timestamp": now.isoformat(),
        "log_date": now.strftime('%Y-%m-%d'),
        "level": level,
        "log": message,
        "data": log_data if log_data else None,
        "session_id": str(session_id) if session_id else None
    }

    try:
        logs_container.create_item(body=item)
    except exceptions.CosmosHttpResponseError as e:
        print(f"Error logging to Cosmos: {e.message}")
    except Exception as e:
        print(f"Unexpected error logging to Cosmos: {e}")


@app.route('/core_prompt/get', methods=['GET'])
def get_prompt():
    conn2 = None  # kept for log_message() call-site compatibility, unused
    log_message(conn2, "info", "fetch core prompt API accessed")

    auth_error = validate_bearer_token(request, 'A7x!G2p@Q9#L')
    if auth_error:
        log_message(conn2, "Error", "error with auth section", {"error": str(auth_error)})
        return auth_error

    try:
        query = """
            SELECT TOP 1 * FROM c
            WHERE c.type = 'contextsense_core_prompt'
            ORDER BY c.core_prompt_id DESC
        """
        results = list(container.query_items(query=query, enable_cross_partition_query=True))
        log_message(conn2, "info", "Fetched latest core_prompt", {"found": len(results) > 0})

        if not results:
            log_message(conn2, "error", "No record found in db error code:404")
            return jsonify({"message": "No records found"}), 404

        doc = results[0]
        log_message(conn2, "info", "DB responded", {"result": str(doc)})

        created_at_dt = datetime.fromisoformat(doc["created_at"]) if doc["created_at"] else None
        response_data = {
            "core_prompt_id": doc["core_prompt_id"],
            "prompt": doc["prompt"],
            "created_by": doc["created_by"],
            "created_at": created_at_dt.strftime('%a, %d %b %Y %H:%M:%S GMT') if created_at_dt else None
        }

        log_message(conn2, "info", "fetch core prompt API responded", {"data": str(response_data)})
        return jsonify(response_data), 200

    except exceptions.CosmosHttpResponseError as e:
        log_message(conn2, "error", "fetch core prompt Api failed", {"error": str(e.message)})
        return jsonify({"error": str(e.message)}), 500
    except Exception as e:
        log_message(conn2, "error", "fetch core prompt Api failed", {"error": str(e)})
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)