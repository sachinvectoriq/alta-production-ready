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
container = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME')).get_container_client('user_text_trans_log')

EXCLUDED_USERS = [
    'Vinayak Inamadar', 'Chanbasava Koti', 'Sherlock5', 'Sachin Bhusanurmath',
    'Dinesh Rout', 'Santosh Sohani', 'Bharatkumar Salalli', 'Vinayak Inamadhar',
    'Harsh Aneppanavar', 'test', 'test1', 'test2', 'test3', 'test4', 'test5', 'Test User', 'test6', 'test7',
    'postman_test_user', 'John Doe', 'Chanbasav Koti', 'Raqib Rasheed', 'undefined', 'test_user123', 'Sherlock', 'Sherlock3', 'Sherlock2', 'Sherlock4'
]

# NOTE: mapped to actual DDL column names -- 'character_count' -> billed_characters,
# same mismatch pattern flagged and confirmed on doc_data_report.
TEXT_TRANS_FILTERABLE_COLS = {
    'user': 'user',
    'source_text': 'source_text',
    'translated_text': 'translated_text',
    'source_language': 'source_language',
    'target_language': 'target_language',
    'billed_characters': 'billed_characters',
    'vendor': 'vendor',
    'refinement_used': 'refinement_used',
    'domain_name': 'domain_name'
}

# NOTE: "session" mapped to login_session_id (the DDL has no plain
# session_id column, matches the correction confirmed for doc_data_report).
order_dict = {
    "id": "user",
    "input": "source_text",
    "output": "translated_text",
    "from": "source_language",
    "to": "target_language",
    "length": "billed_characters",
    "provider": "vendor",
    "timestamp": "date_and_time",
    "log": "log_id",
    "refined": "refinement_used",
    "session": "login_session_id",
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


@app.route('/text_data_report', methods=['GET'])
def get_text_data_report():

    user_name = request.args.get('user_name', None)
    print(f"INFO: API endpoint to get text data report accessed by user: {user_name}")

    auth_error = validate_bearer_token(request, 'A7x!G2p@Q9#L', user_name)
    if auth_error:
        return auth_error

    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    pageno_str = request.args.get('page')
    limit_str = request.args.get('limit')
    order_str = request.args.get('order', 'timestamp')
    orderby_str = request.args.get('orderby', 'asc')
    export_str = request.args.get('export', '0')
    export = int(export_str)
    domain_name = request.args.get('domain_name', False)

    start_date = None
    end_date = None
    limit = 100
    page = 1
    offset = 0

    try:
        if limit_str:
            limit = int(limit_str)
            if limit <= 0:
                raise ValueError("Limit must be a positive integer.")
        print(f"INFO: Parsed limit: {limit}")
    except ValueError as e:
        print(f"WARNING: Invalid limit parameter: {limit_str}. Error: {e}")
        return jsonify({"error": f"Invalid limit parameter: {limit_str}. Must be a positive integer."}), 400

    try:
        if pageno_str:
            page = int(pageno_str)
            if page <= 0:
                raise ValueError("Page number must be a positive integer.")
        offset = (page - 1) * limit
        print(f"INFO: Parsed pagination: page={page}, offset={offset}")
    except ValueError as e:
        print(f"WARNING: Invalid page parameter: {pageno_str}. Error: {e}")
        return jsonify({"error": f"Invalid page parameter: {pageno_str}. Must be a positive integer."}), 400

    if start_date_str:
        try:
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
            print(f"INFO: Parsed start_date: {start_date}")
        except ValueError:
            print(f"WARNING: Invalid start_date format: {start_date_str}")
            return jsonify({"error": "Invalid start_date format. Use YYYY-MM-DD."}), 400

    if end_date_str:
        try:
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
            end_date = datetime.datetime.combine(end_date, datetime.time(23, 59, 59))
            print(f"INFO: Parsed end_date: {end_date}")
        except ValueError:
            print(f"WARNING: Invalid end_date format: {end_date_str}")
            return jsonify({"error": "Invalid end_date format. Use YYYY-MM-DD."}), 400

    if start_date and end_date and start_date > end_date.date():
        print("WARNING: start_date cannot be after end_date.")
        return jsonify({"error": "start_date cannot be after end_date."}), 400

    try:
        print("INFO: Building query for text data report.")

        conditions = ["c.type = 'user_text_trans_log'"]
        params = []
        param_counter = 0

        def next_param():
            nonlocal param_counter
            param_counter += 1
            return f"@p{param_counter}"

        if start_date:
            p = next_param()
            conditions.append(f"c.date_and_time >= {p}")
            params.append({"name": p, "value": start_date.isoformat()})
        if end_date:
            p = next_param()
            conditions.append(f"c.date_and_time <= {p}")
            params.append({"name": p, "value": end_date.isoformat()})

        if domain_name:
            p = next_param()
            conditions.append(f"c.domain_name = {p}")
            params.append({"name": p, "value": domain_name})

        if EXCLUDED_USERS:
            p = next_param()
            conditions.append(f"NOT ARRAY_CONTAINS({p}, c.user)")
            params.append({"name": p, "value": EXCLUDED_USERS})
            print(f"INFO: Excluding {len(EXCLUDED_USERS)} users from text data report.")

        for param_key, param_value in request.args.items():
            if param_key in ['start_date', 'end_date', 'limit', 'page', 'user_name']:
                continue

            if param_key in TEXT_TRANS_FILTERABLE_COLS:
                db_column = TEXT_TRANS_FILTERABLE_COLS[param_key]
                if param_key == 'billed_characters':
                    try:
                        int_value = int(param_value)
                        p = next_param()
                        conditions.append(f"c.{db_column} = {p}")
                        params.append({"name": p, "value": int_value})
                        print(f"INFO: Added integer filter: {param_key}={int_value}")
                    except ValueError:
                        print(f"WARNING: Invalid integer value for {param_key}: {param_value}")
                        return jsonify({"error": f"Invalid value for {param_key}. Must be an integer."}), 400
                elif param_key == 'refinement_used':
                    if param_value.lower() in ['true', '1', 'yes']:
                        bool_value = True
                    elif param_value.lower() in ['false', '0', 'no']:
                        bool_value = False
                    else:
                        print(f"WARNING: Invalid boolean value for {param_key}: {param_value}")
                        return jsonify({"error": f"Invalid value for {param_key}. Must be 'true' or 'false'."}), 400
                    p = next_param()
                    conditions.append(f"c.{db_column} = {p}")
                    params.append({"name": p, "value": bool_value})
                    print(f"INFO: Added boolean filter: {param_key}={bool_value}")
                else:
                    p = next_param()
                    conditions.append(f"c.{db_column} = {p}")
                    params.append({"name": p, "value": param_value})
                    print(f"INFO: Added string filter: {param_key}={param_value}")
            else:
                print(f"WARNING: Ignoring unrecognized query parameter for filtering: {param_key}")

        if len(conditions) == 1:
            print("INFO: Fetching all text data (no date or user filters).")

        where_clause = " AND ".join(conditions)

        count_query = f"SELECT VALUE COUNT(1) FROM c WHERE {where_clause}"
        count_result = list(container.query_items(query=count_query, parameters=params, enable_cross_partition_query=True))
        row_count = count_result[0] if count_result else 0

        select_fields = ("c.date_and_time, c.source_text, c.source_language, c.target_language, "
                         "c.translated_text, c.user, c.vendor, c.billed_characters, "
                         "c.refinement_used, c.domain_name")

        data_query = f"SELECT {select_fields} FROM c WHERE {where_clause}"

        if order_str in order_dict:
            if orderby_str.lower() not in ['asc', 'desc']:
                print(f"WARNING: Invalid orderby parameter: {orderby_str}. Defaulting to 'asc'.")
                orderby_str = 'asc'
            data_query += f" ORDER BY c.{order_dict[order_str]} {orderby_str.upper()}"

        data_query += f" OFFSET {offset} LIMIT {limit}"

        print(f"INFO: Executing query for text data: {data_query}")
        print(f"INFO: Query parameters: {params}")
        rows = list(container.query_items(query=data_query, parameters=params, enable_cross_partition_query=True))

        # only domain_name -> opco is a real alias in the original query
        for r in rows:
            if 'domain_name' in r:
                r['opco'] = r.pop('domain_name')

        if export == 1:
            df = pd.DataFrame(rows)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Sheet1')
            output.seek(0)
            return send_file(output, download_name="text_report.xlsx", as_attachment=True)

        print(f"INFO: Successfully fetched {len(rows)} text data records.")
        return jsonify({'data': rows, 'total_rows': row_count}), 200

    except exceptions.CosmosHttpResponseError as db_error:
        print(f"ERROR: Database error while fetching text data report: {db_error}")
        return jsonify({"error": f"Database error: {db_error.message}"}), 500
    except Exception as e:
        print(f"CRITICAL: An unexpected error occurred while fetching text data report: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    try:
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        print(f"CRITICAL: Flask text_report application failed to start: {e}")
    finally:
        print("INFO: Flask text_report application is shutting down.")
