from flask import Flask, request, jsonify
from azure.cosmos import CosmosClient, exceptions
from azure.core import MatchConditions
from dotenv import load_dotenv
from datetime import datetime, timezone
import uuid
import os

load_dotenv()

app = Flask(__name__)

cosmos_client = CosmosClient(os.getenv('COSMOS_ENDPOINT'), os.getenv('COSMOS_KEY'))
database = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME'))
container = database.get_container_client('alta_reports_access')


def get_next_access_id():
    """Atomically increments the counter document for access_id."""
    while True:
        counter = container.read_item(item='counter_access_id', partition_key='__counter__')
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


def email_exists(email):
    """Fast single-partition check, since email is the partition key."""
    query = "SELECT VALUE COUNT(1) FROM c WHERE c.type = 'alta_reports_access' AND c.email = @email"
    params = [{"name": "@email", "value": email}]
    result = list(container.query_items(query=query, parameters=params, partition_key=email))
    return result[0] > 0


def insert_access_record(name, email, granted_by):
    """
    Function to insert a new record into alta_reports_access container.
    Mirrors original Postgres behavior, including the UNIQUE(email) constraint.
    """
    try:
        if email_exists(email):
            return {'success': False, 'error': 'Email address already exists'}

        access_id = get_next_access_id()
        granted_at = datetime.now(timezone.utc).isoformat()

        item = {
            "id": str(uuid.uuid4()),
            "type": "alta_reports_access",
            "access_id": access_id,
            "name": name,
            "email": email,
            "permission_granted_at": granted_at,
            "granted_by": granted_by
        }

        container.create_item(body=item)

        return {
            'success': True,
            'record_id': access_id,
            'permission_granted_at': granted_at,
            'message': 'Record inserted successfully'
        }

    except exceptions.CosmosHttpResponseError as e:
        return {'success': False, 'error': f'Database error: {e.message}'}
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {e}'}


def delete_access_record(record_id):
    """
    Function to delete a record from alta_reports_access container.
    """
    try:
        query = "SELECT * FROM c WHERE c.type = 'alta_reports_access' AND c.access_id = @access_id"
        params = [{"name": "@access_id", "value": record_id}]
        results = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))

        if not results:
            return {'success': False, 'error': 'Record not found'}

        doc = results[0]
        deleted_record = {
            "id": doc["access_id"],
            "name": doc["name"],
            "email": doc["email"],
            "permission_granted_at": doc["permission_granted_at"],
            "granted_by": doc["granted_by"]
        }

        container.delete_item(item=doc['id'], partition_key=doc['email'])

        return {
            'success': True,
            'deleted_record': deleted_record,
            'message': 'Record deleted successfully'
        }

    except exceptions.CosmosHttpResponseError as e:
        return {'success': False, 'error': f'Database error: {e.message}'}
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {e}'}


def fetch_access_records(record_id=None, email=None, limit=None):
    """
    Function to fetch records from alta_reports_access container.
    """
    try:
        conditions = ["c.type = 'alta_reports_access'"]
        params = []

        if record_id is not None:
            conditions.append("c.access_id = @access_id")
            params.append({"name": "@access_id", "value": record_id})

        if email is not None:
            conditions.append("c.email = @email")
            params.append({"name": "@email", "value": email})

        query = f"SELECT * FROM c WHERE {' AND '.join(conditions)} ORDER BY c.permission_granted_at DESC"

        # If filtering by email, we can scope to a single partition; otherwise cross-partition
        if email is not None:
            results = list(container.query_items(query=query, parameters=params, partition_key=email))
        else:
            results = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))

        if limit is not None:
            results = results[:limit]

        records = [{
            "id": r["access_id"],
            "name": r["name"],
            "email": r["email"],
            "permission_granted_at": r["permission_granted_at"],
            "granted_by": r["granted_by"]
        } for r in results]

        return {
            'success': True,
            'records': records,
            'count': len(records),
            'message': f'Fetched {len(records)} records successfully'
        }

    except exceptions.CosmosHttpResponseError as e:
        return {'success': False, 'error': f'Database error: {e.message}'}
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {e}'}


# Flask Routes

@app.route('/insert_access', methods=['POST'])
def insert_access_endpoint():
    data = request.get_json()

    if not data or not isinstance(data, dict):
        return jsonify({'error': "Invalid input. Expecting a dictionary."}), 400

    required_fields = ['name', 'email', 'granted_by']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f"Missing required field: {field}"}), 400

    result = insert_access_record(data['name'], data['email'], data['granted_by'])

    if result['success']:
        return jsonify(result), 201
    else:
        return jsonify(result), 400


@app.route('/delete_access/<int:record_id>', methods=['DELETE'])
def delete_access_endpoint(record_id):
    result = delete_access_record(record_id)

    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 404


@app.route('/fetch_access', methods=['GET'])
def fetch_access_endpoint():
    record_id = request.args.get('record_id', type=int)
    email = request.args.get('email')
    limit = request.args.get('limit', type=int)

    result = fetch_access_records(record_id, email, limit)

    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 500


@app.route('/health', methods=['GET'])
def health_check():
    try:
        # Simple connectivity check — read the counter doc
        container.read_item(item='counter_access_id', partition_key='__counter__')
        return jsonify({'status': 'healthy', 'database': 'connected'}), 200
    except Exception:
        return jsonify({'status': 'unhealthy', 'database': 'disconnected'}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="127.0.0.1", port=port, debug=True, threaded=False, processes=1)