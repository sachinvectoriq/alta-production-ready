from flask import Flask, request, jsonify
from azure.cosmos import CosmosClient
from dotenv import load_dotenv
from datetime import datetime, timezone
import os

load_dotenv()
app = Flask(__name__)

cosmos_client = CosmosClient(os.getenv('COSMOS_ENDPOINT'), os.getenv('COSMOS_KEY'))
container = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME')).get_container_client('alta_filters')


@app.route('/update_filter', methods=['PUT'])
def update_filter():
    try:
        filter_id = request.args.get('id')
        if not filter_id:
            return jsonify({"error": "Missing required parameter: id"}), 400
        filter_id = int(filter_id)

        modifier = request.args.get('modifier')
        value = request.args.get('value')
        system_prompt = request.args.get('system_prompt')
        user_prompt = request.args.get('user_prompt')
        created_by = request.args.get('created_by')

        update_fields = {}
        if modifier is not None:
            update_fields['modifier'] = modifier
        if value is not None:
            update_fields['value'] = value
        if system_prompt is not None:
            update_fields['system_prompt'] = system_prompt
        if user_prompt is not None:
            update_fields['user_prompt'] = user_prompt
        if created_by is not None:
            update_fields['created_by'] = created_by

        if not update_fields:
            return jsonify({"error": "No update parameters provided"}), 400

        # NOTE: created_at is deliberately never included here — this preserves
        # the original Postgres trigger's guarantee that created_at is immutable after insert.
        update_fields['updated_at'] = datetime.now(timezone.utc).isoformat()

        # Find the item first — need its Cosmos id + partition key (modifier) to update it
        query = "SELECT * FROM c WHERE c.type = 'alta_filters' AND c.filter_id = @filter_id"
        params = [{"name": "@filter_id", "value": filter_id}]
        results = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))

        if not results:
            return jsonify({"error": f"No filter found with id {filter_id}"}), 404

        doc = results[0]
        original_partition_value = doc["modifier"]  # needed even if modifier itself is changing

        doc.update(update_fields)

        # If modifier (the partition key) is changing, Cosmos requires delete + recreate
        # rather than an in-place update, since partition key values are immutable per item.
        if 'modifier' in update_fields and update_fields['modifier'] != original_partition_value:
            container.delete_item(item=doc['id'], partition_key=original_partition_value)
            container.create_item(body=doc)
        else:
            container.replace_item(item=doc['id'], body=doc)

        updated_data = {
            "id": doc["filter_id"],
            "modifier": doc["modifier"],
            "system": doc["system_prompt"],
            "user": doc["user_prompt"],
            "value": doc["value"]
        }

        return jsonify({
            "data": updated_data,
            "message": f"Filter with id {filter_id} updated successfully",
            "rows_affected": 1
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)