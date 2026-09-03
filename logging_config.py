import os
from datetime import datetime, timezone
import threading
from typing import List, Dict, Tuple, Optional, Any
import logging
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from azure.cosmos import CosmosClient, exceptions
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)

cosmos_client = CosmosClient(os.getenv('COSMOS_ENDPOINT'), os.getenv('COSMOS_KEY'))
database = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME'))
container = database.get_container_client('alta_logs')

# --- Thread-safe In-Memory Logging Buffer ---
LOG_BUFFER: List[Dict] = []
LOG_LOCK = threading.Lock()
MAX_BUFFER_SIZE = 1000


def log(level: str, message: str, data: Any = None, user_name: Optional[str] = None):
    now = datetime.now(timezone.utc)

    log_entry = {
        "id": str(uuid.uuid4()),
        "type": "alta_logs",
        "timestamp": now.isoformat(),
        "log_date": now.strftime('%Y-%m-%d'),
        "level": level,
        "message": message,
        "data": data if isinstance(data, (dict, list)) else None,
        "user_name": user_name
    }

    with LOG_LOCK:
        LOG_BUFFER.append(log_entry)


def flush() -> Tuple[bool, str]:
    """
    Flushes the in-memory buffer to Cosmos. Cosmos has no multi-row
    INSERT like executemany(), so entries are written concurrently
    via a small thread pool instead of one at a time sequentially.
    """
    with LOG_LOCK:
        if not LOG_BUFFER:
            message = "No logs to flush."
            logging.info(message)
            return True, message

        buffer_copy = LOG_BUFFER[:]
        LOG_BUFFER.clear()

    failed_entries = []

    def write_entry(entry):
        try:
            container.create_item(body=entry)
            return None
        except exceptions.CosmosHttpResponseError as e:
            return entry

    try:
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(write_entry, entry) for entry in buffer_copy]
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    failed_entries.append(result)

        if failed_entries:
            with LOG_LOCK:
                LOG_BUFFER.extend(failed_entries)
            message = f"Flush partially failed: {len(failed_entries)} of {len(buffer_copy)} entries failed. Restoring failed entries to buffer."
            logging.warning(message)
            return False, message

        message = "Flush successful."
        logging.info(message)
        return True, message

    except Exception as e:
        with LOG_LOCK:
            LOG_BUFFER.extend(buffer_copy)
        message = f"Flush failed with error: {e}"
        logging.exception("Flush failed:")
        return False, message