from flask import Flask, request, jsonify
from azure.cosmos import CosmosClient, exceptions
from azure.core import MatchConditions
from dotenv import load_dotenv
from datetime import datetime, timezone
import uuid
import os

load_dotenv()

app = Flask(__name__)

# Cosmos DB configuration
cosmos_client = CosmosClient(os.getenv('COSMOS_ENDPOINT'), os.getenv('COSMOS_KEY'))
database = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME'))
container = database.get_container_client('user_login_log')


def get_next_login_session_id():
    """
    Atomically increments the counter document to get the next login_session_id.
    Retries automatically if a concurrent write conflict occurs.
    """
    while True:
        counter = container.read_item(item='counter_login_session_id', partition_key='counter_login_session_id')
        next_val = counter['value'] + 1
        counter['value'] = next_val
        try:
            container.replace_item(
                item=counter,
                body=counter,
                etag=counter['_etag'],
                match_condition=MatchConditions.IfNotModified
            )
            return next_val
        except exceptions.CosmosAccessConditionFailedError:
            continue  # another request updated it first, retry


@app.route('/log_user_login', methods=['POST'])
def log_user_login():
    """
    Endpoint to log user login details.
    Expects form data input: {"user": "username"}
    """
    user = request.form.get('user')  # Fetch 'user' from form data
    domain_name = request.form.get('domain_name', False)

    if not user:
        return jsonify({"error": "The 'user' field is required."}), 400

    try:
        login_session_id = get_next_login_session_id()

        item = {
            "id": str(uuid.uuid4()),
            "type": "user_login_log",
            "user": user,
            "login_session_id": login_session_id,
            "login_date_and_time": datetime.now(timezone.utc).isoformat(),
            "domain_name": domain_name if domain_name else None
        }

        container.create_item(body=item)

        return jsonify({"message": "Login details added successfully.",
                        "login_session_id": login_session_id}), 201
    except exceptions.CosmosHttpResponseError as e:
        return jsonify({"error": f"Database error: {e.message}"}), 500


if __name__ == '__main__':
    app.run(debug=True)