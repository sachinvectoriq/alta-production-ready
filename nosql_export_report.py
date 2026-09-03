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

# Define allowed containers for security
ALLOWED_CONTAINERS = [
    'contextsense',
    'user_docu_trans_log',
    'user_text_trans_log',
    'user_login_log'
]

EXCLUDED_USERS = [
    'Vinayak Inamadar', 'Chanbasava Koti', 'Sherlock5', 'Sachin Bhusanurmath',
    'Dinesh Rout', 'Santosh Sohani', 'Bharatkumar Salalli', 'Vinayak Inamadhar',
    'Harsh Aneppanavar', 'test', 'test1', 'test2', 'test3', 'test4', 'test5', 'Test User', 'test6', 'test7',
    'postman_test_user', 'test_user', 'John Doe', 'Chanbasav Koti', 'Raqib Rasheed', 'undefined', 'test_user123',
    'Sherlock', 'Sherlock3', 'Sherlock2', 'Sherlock4'
]


def validate_bearer_token(request, expected_token, user_name: str = None):
    auth_header = request.headers.get('Authorization', '')
    parts = auth_header.split(' ')
    if not auth_header.startswith('Bearer ') or len(parts) != 2:
        return jsonify({"error": "Invalid or missing Authorization header."}), 401

    token = parts[1]

    if token != expected_token:
        return jsonify({"error": "Unauthorized. Invalid Bearer token."}), 403

    return None


def export_table_data():
    user_name = request.args.get('user_name', None)
    table_name = request.args.get('table_name')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    auth_error = validate_bearer_token(request, 'A7x!G2p@Q9#L', user_name)
    if auth_error:
        return auth_error

    if not table_name or table_name not in ALLOWED_CONTAINERS:
        return jsonify({"error": f"Invalid table_name. Must be one of: {', '.join(ALLOWED_CONTAINERS)}"}), 400

    try:
        container = database.get_container_client(table_name)
        
        # Build query
        query = f"SELECT * FROM c WHERE c.type = '{table_name}'"
        
        # Add date filtering if provided
        if start_date_str:
            try:
                start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
                query += f" AND c.date_and_time >= '{start_date.isoformat()}T00:00:00'"
            except ValueError:
                return jsonify({"error": "Invalid start_date format. Use YYYY-MM-DD."}), 400

        if end_date_str:
            try:
                end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
                query += f" AND c.date_and_time <= '{end_date.isoformat()}T23:59:59'"
            except ValueError:
                return jsonify({"error": "Invalid end_date format. Use YYYY-MM-DD."}), 400

        # Exclude test users
        for excluded_user in EXCLUDED_USERS:
            query += f" AND c.user != '{excluded_user}'"

        items = list(container.query_items(query=query, enable_cross_partition_query=True))

        if not items:
            return jsonify({"error": "No data found for the specified criteria."}), 404

        # Convert to DataFrame
        df = pd.DataFrame(items)
        
        # Drop unnecessary columns
        df = df.drop(columns=['id'], errors='ignore')

        # Create Excel file in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name=table_name)
        output.seek(0)

        # Return file
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'{table_name}_export_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )

    except exceptions.CosmosHttpResponseError as e:
        print(f"ERROR: Database error: {e.message}")
        return jsonify({"error": f"Database error: {e.message}"}), 500
    except Exception as e:
        print(f"ERROR: Unexpected error: {str(e)}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
