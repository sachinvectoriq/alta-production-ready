from flask import Flask, request, jsonify
from azure.cosmos import CosmosClient, exceptions
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

print("Starting token limit update server")


# ============================================================
# Cosmos DB Configuration
# ============================================================

cosmos_client = CosmosClient(
    os.getenv('COSMOS_ENDPOINT'),
    os.getenv('COSMOS_KEY')
)

database = cosmos_client.get_database_client(
    os.getenv('COSMOS_DB_NAME')
)

container = database.get_container_client(
    'alta_var_settings'
)


# ============================================================
# Update Token Limit
# ============================================================

def nosql_update_token_limit():

    """
    Updates the token_limit value in the
    alta_var_settings Cosmos DB container.

    Expected JSON:
    {
        "token_limit": 5000
    }
    """

    # --------------------------------------------------------
    # Get JSON request body
    # --------------------------------------------------------

    data = request.get_json()

    print("Received request data:", data)

    if not data or not isinstance(data, dict) or 'token_limit' not in data:

        print(
            "Invalid input. "
            "Expected a dictionary with a 'token_limit' key."
        )

        return jsonify({
            'error': (
                "Invalid input. "
                "Expected a dictionary with a 'token_limit' key."
            )
        }), 400


    # --------------------------------------------------------
    # Get token limit
    # --------------------------------------------------------

    token_limit = data['token_limit']

    print("Requested token_limit:", token_limit)


    # --------------------------------------------------------
    # Validate token limit
    # --------------------------------------------------------

    try:
        token_limit = int(token_limit)

    except (ValueError, TypeError):

        print("token_limit must be an integer")

        return jsonify({
            "error": "token_limit must be an integer"
        }), 400


    # --------------------------------------------------------
    # Find token_limit document
    # --------------------------------------------------------

    try:

        query = """
            SELECT *
            FROM c
            WHERE c["type"] = "alta_var_settings"
              AND c["key"] = "token_limit"
        """

        print("Executing Cosmos DB query:")
        print(query)

        results = list(
            container.query_items(
                query=query,
                enable_cross_partition_query=True
            )
        )

        print("Query results:", results)


        # ----------------------------------------------------
        # Check if document exists
        # ----------------------------------------------------

        if not results:

            print("token_limit document not found")

            return jsonify({
                "error": "token_limit not found in database"
            }), 404


        # ----------------------------------------------------
        # Get existing document
        # ----------------------------------------------------

        document = results[0]

        print("Existing document:", document)


        # ----------------------------------------------------
        # Update value
        # ----------------------------------------------------

        document["value"] = str(token_limit)

        print(
            "Updating token_limit to:",
            document["value"]
        )


        # ----------------------------------------------------
        # Replace document in Cosmos DB
        # ----------------------------------------------------

        container.replace_item(
            item=document["id"],
            body=document
        )

        print("Token limit updated successfully")


        return jsonify({
            "message": "Token limit updated successfully.",
            "token_limit": token_limit
        }), 200


    except exceptions.CosmosHttpResponseError as e:

        print("Cosmos DB error:")
        print(str(e))

        return jsonify({
            "error": f"Database error: {str(e)}"
        }), 500


    except Exception as e:

        print("Unexpected error:")
        print(str(e))

        return jsonify({
            "error": f"Unexpected error: {str(e)}"
        }), 500


# ============================================================
# Start Flask Server
# ============================================================

if __name__ == '__main__':

    port = int(
        os.environ.get("PORT", 5000)
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )