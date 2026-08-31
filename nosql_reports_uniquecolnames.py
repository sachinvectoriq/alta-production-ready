from flask import Flask, request, jsonify
from azure.cosmos import CosmosClient, exceptions
from dotenv import load_dotenv
import os
from logging_config import log, flush

load_dotenv()
app = Flask(__name__)

cosmos_client = CosmosClient(os.getenv('COSMOS_ENDPOINT'), os.getenv('COSMOS_KEY'))
database = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME'))


@app.route('/unique-values', methods=['GET'])
def get_unique_values():
    """
    API endpoint to fetch unique values from a specified field in a
    specified container. Requires 'table_name' (container id) and
    'column_name' (field name) as query parameters.
    """
    table_name = request.args.get('table_name')
    column_name = request.args.get('column_name')

    if not table_name or not column_name:
        log("WARNING", "Missing table_name or column_name in request parameters.", data={"action": "unique_values_request_fail"})
        flush()
        return jsonify({"error": "Missing 'table_name' or 'column_name' query parameter"}), 400

    try:
        try:
            container = database.get_container_client(table_name)
            # Force a check that the container actually exists
            container.read()
        except exceptions.CosmosResourceNotFoundError:
            log("ERROR", f"Database error: Container '{table_name}' does not exist.", data={"action": "db_query_fail"})
            flush()
            return jsonify({"error": f"Table '{table_name}' does not exist"}), 404

        log("INFO", f"Executing query to fetch unique values for column {column_name} in table {table_name}.")

        query = f"SELECT DISTINCT VALUE c.{column_name} FROM c"
        results = list(container.query_items(query=query, enable_cross_partition_query=True))

        # If the column genuinely doesn't exist on any document, Cosmos
        # returns an empty list rather than an error (unlike Postgres,
        # which raises UndefinedColumn) -- flagged as a behavior difference.
        unique_values = results

        log("INFO", f"Successfully fetched {len(unique_values)} unique values.")
        flush()
        return jsonify({"table": table_name, "column": column_name, "unique_values": unique_values})

    except exceptions.CosmosHttpResponseError as e:
        log("ERROR", f"Database error while fetching unique values: {e}", data={"action": "db_query_fail"})
        flush()
        return jsonify({"error": f"Database error: {e.message}"}), 500
    except Exception as e:
        log("CRITICAL", f"An unexpected error occurred: {e}", data={"action": "unexpected_error"})
        flush()
        return jsonify({"error": "An unexpected server error occurred"}), 500


if __name__ == '__main__':
    app.run(debug=True)