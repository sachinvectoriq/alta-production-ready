from flask import Flask, request, jsonify
from azure.cosmos import CosmosClient, exceptions
from azure.core import MatchConditions
from dotenv import load_dotenv
import uuid
import os

load_dotenv()

app = Flask(__name__)

cosmos_client = CosmosClient(os.getenv('COSMOS_ENDPOINT'), os.getenv('COSMOS_KEY'))
database = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME'))
container = database.get_container_client('contextsense')
trans_log_container = database.get_container_client('user_text_trans_log')


def get_next_selection_id():
    """Atomically increments the counter document for selection_id."""
    while True:
        counter = container.read_item(item='counter_selection_id', partition_key='__counter__')
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
            continue


def insert_context_selection(login_session_id, modifier_type, modifier_value,
                               system_prompt, user_prompt, refined_text, explanation, domain_name):
    """
    Inserts a single context selection into the contextsense container.
    Returns the created item so it can be rolled back if the paired
    user_text_trans_log update fails.
    """
    selection_id = get_next_selection_id()

    item = {
        "id": str(uuid.uuid4()),
        "type": "contextsense",
        "selection_id": selection_id,
        "login_session_id": login_session_id,
        "modifier_type": modifier_type,
        "modifier_value": modifier_value,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "refined_text": refined_text,
        "explanation": explanation,
        "domain_name": domain_name
    }
    container.create_item(body=item)
    print("insert query executed")
    return item


@app.route('/log_contextsense', methods=['POST'])
def log_contextsense():
    """
    Endpoint to log context sense data and update the user_text_trans_log container.
    Expects JSON data with 'login_session_id', 'modifier_types', 'modifier_values',
    'system_prompts', 'user_prompts', 'refined_text', and 'explanation'.
    """
    created_item = None
    try:
        data = request.get_json()
        login_session_id = data.get('login_session_id')
        modifier_types = data.get('modifier_types')
        modifier_values = data.get('modifier_values')
        system_prompts = data.get('system_prompts')
        user_prompts = data.get('user_prompts')
        refined_text = data.get('refined_text')
        explanation = data.get('explanation')
        domain_name = data.get('domain_name', False)
        print(data)

        if not all([login_session_id, modifier_types, modifier_values, system_prompts, user_prompts, refined_text, explanation]):
            return jsonify({"error": "Missing required data in the JSON payload."}), 400

        if not (isinstance(modifier_types, list) and isinstance(modifier_values, list)):
            return jsonify({"error": "modifier_types, modifier_values, system_prompts, and user_prompts must be lists."}), 400

        if not (len(modifier_types) == len(modifier_values)):
            return jsonify({"error": "modifier_types, modifier_values, system_prompts, and user_prompts must have the same number of elements."}), 400

        created_item = insert_context_selection(
            login_session_id, str(modifier_types), str(modifier_values),
            system_prompts, user_prompts, refined_text, explanation, domain_name
        )

        # Update refinement_used in user_text_trans_log.
        # This is a best-effort second write (Cosmos has no cross-container
        # transactions), so we compensate by rolling back the contextsense
        # insert above if this update fails -- approximating the atomicity
        # the original Postgres transaction guaranteed.
        try:
            query = "SELECT * FROM c WHERE c.type = 'user_text_trans_log' AND c.login_session_id = @sid"
            params = [{"name": "@sid", "value": login_session_id}]
            matches = list(trans_log_container.query_items(
                query=query, parameters=params, partition_key=login_session_id
            ))
            for doc in matches:
                doc['refinement_used'] = True
                trans_log_container.replace_item(item=doc['id'], body=doc)
            print(f"Updated user_text_trans_log for {len(matches)} matching row(s)")
        except Exception as update_error:
            container.delete_item(item=created_item['id'], partition_key=created_item['login_session_id'])
            return jsonify({"error": f"Failed to update user_text_trans_log, insert rolled back: {update_error}"}), 500

        return jsonify({"message": "Context sense data logged successfully."}), 200

    except exceptions.CosmosHttpResponseError as e:
        if created_item:
            try:
                container.delete_item(item=created_item['id'], partition_key=created_item['login_session_id'])
            except Exception:
                pass
        return jsonify({"error": f"Database error: {e.message}"}), 500
    except Exception as e:
        return jsonify({"error": f"Error processing request: {e}"}), 500


if __name__ == '__main__':
    app.run(debug=True)