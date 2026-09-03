import os
from flask import Flask, request, jsonify, send_file
from azure.cosmos import CosmosClient, exceptions
from dotenv import load_dotenv
import datetime
import pandas as pd
from io import BytesIO

load_dotenv()

app = Flask(__name__)

cosmos_client = CosmosClient(os.getenv('COSMOS_ENDPOINT'), os.getenv('COSMOS_KEY'))
database = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME'))
contextsense_container = database.get_container_client('contextsense')
trans_log_container = database.get_container_client('user_text_trans_log')

EXCLUDED_USERS = [
    'Vinayak Inamadar', 'Chanbasava Koti', 'Sherlock5', 'Sachin Bhusanurmath',
    'Dinesh Rout', 'Santosh Sohani', 'Bharatkumar Salalli', 'Vinayak Inamadhar',
    'Harsh Aneppanavar', 'test', 'test1', 'test2', 'test3', 'test4', 'test5', 'Test User', 'test6', 'test7',
    'postman_test_user', 'test_user', 'John Doe', 'Chanbasav Koti', 'Raqib Rasheed', 'undefined', 'test_user123',
    'Sherlock', 'Sherlock3', 'Sherlock2', 'Sherlock4'
]

CONTEXTSENSE_FILTERABLE_COLS = {
    'modifier_type': 'modifier_type',
    'modifier_value': 'modifier_value',
    'user': 'user',
    'source_language': 'source_language',
    'target_language': 'target_language',
    'billed_characters': 'billed_characters',
    'vendor': 'vendor',
    'domain_name': 'domain_name'
}

order_dict = {
    "id": "user",
    "modifier": "modifier_type",
    "modifier_value": "modifier_value",
    "from": "source_language",
    "to": "target_language",
    "length": "billed_characters",
    "provider": "vendor",
    "timestamp": "date_and_time",
    "refined": "refined_text",
    "explanation": "explanation",
    "domain_name": "domain_name"
}


def validate_bearer_token(request, expected_token, user_name: str = None):
    auth_header = request.headers.get('Authorization', '')
    print(f"INFO: Attempting to validate Bearer token. Auth header present: {bool(auth_header)}")

    parts = auth_header.split(' ')
    if not auth_header.startswith('Bearer ') or len(parts) != 2:
        print(f"WARNING: Invalid or missing Authorization header format. Header: '{auth_header}'")
        return jsonify({"error": "Invalid or missing Authorization header."}), 401

    token = parts[1]

    if token != expected_token:
        print(f"ERROR: Unauthorized access attempt: Invalid Bearer token. Provided token prefix: {token[:5]}...")
        return jsonify({"error": "Unauthorized. Invalid Bearer token."}), 403

    print("INFO: Bearer token validated successfully.")
    return None


@app.route('/contextsense_data_report', methods=['GET'])
def get_contextsense_data_report():
    user_name = request.args.get('user_name', None)
    print(f"INFO: API endpoint to get contextsense data report accessed by user: {user_name}")

    auth_error = validate_bearer_token(request, 'A7x!G2p@Q9#L', user_name)
    if auth_error:
        return auth_error

    # Parse query parameters
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    pageno_str = request.args.get('page', '1')
    limit_str = request.args.get('limit', '100')
    domain_name = request.args.get('domain_name')
    sort_by = request.args.get('sort_by', 'date_and_time')
    sort_order = request.args.get('sort_order', 'DESC')

    try:
        limit = int(limit_str)
        if limit <= 0:
            raise ValueError("Limit must be positive")
    except ValueError:
        return jsonify({"error": "Invalid limit parameter. Must be a positive integer."}), 400

    try:
        page = int(pageno_str)
        if page <= 0:
            raise ValueError("Page must be positive")
        offset = (page - 1) * limit
    except ValueError:
        return jsonify({"error": "Invalid page parameter. Must be a positive integer."}), 400

    start_date = None
    end_date = None

    if start_date_str:
        try:
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error": "Invalid start_date format. Use YYYY-MM-DD."}), 400

    if end_date_str:
        try:
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
            end_date = datetime.datetime.combine(end_date, datetime.time(23, 59, 59))
        except ValueError:
            return jsonify({"error": "Invalid end_date format. Use YYYY-MM-DD."}), 400

    if start_date and end_date and start_date > end_date.date():
        return jsonify({"error": "start_date cannot be later than end_date."}), 400

    try:
        # Query contextsense data with optional date filtering
        query = "SELECT * FROM c WHERE c.type = 'contextsense'"
        params = []

        if start_date:
            query += f" AND c.date_and_time >= '{start_date.isoformat()}T00:00:00'"

        if end_date:
            query += f" AND c.date_and_time <= '{end_date.isoformat()}'"

        if domain_name:
            query += f" AND c.domain_name = '{domain_name}'"

        # Exclude test users
        for excluded_user in EXCLUDED_USERS:
            query += f" AND c.user != '{excluded_user}'"

        # Sort and paginate
        if sort_by in order_dict:
            sort_field = order_dict[sort_by]
            query += f" ORDER BY c.{sort_field} {sort_order}"
        else:
            query += f" ORDER BY c.date_and_time DESC"

        query += f" OFFSET {offset} LIMIT {limit}"

        items = list(contextsense_container.query_items(query=query, enable_cross_partition_query=True))

        # Get total count
        count_query = "SELECT VALUE COUNT(1) FROM c WHERE c.type = 'contextsense'"
        if domain_name:
            count_query += f" AND c.domain_name = '{domain_name}'"
        for excluded_user in EXCLUDED_USERS:
            count_query += f" AND c.user != '{excluded_user}'"

        total_count_result = list(contextsense_container.query_items(query=count_query, enable_cross_partition_query=True))
        total_count = total_count_result[0] if total_count_result else 0

        return jsonify({
            "data": items,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": total_count,
                "total_pages": (total_count + limit - 1) // limit
            }
        }), 200

    except exceptions.CosmosHttpResponseError as e:
        print(f"ERROR: Database error: {e.message}")
        return jsonify({"error": f"Database error: {e.message}"}), 500
    except Exception as e:
        print(f"ERROR: Unexpected error: {str(e)}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
