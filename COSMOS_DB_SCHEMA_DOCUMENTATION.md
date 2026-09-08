# Cosmos DB Schema Documentation - Alta Application
## Complete Database Table Structures

---

## 📋 Overview

**Database Name:** `cosmos-alta-qa-001`  
**Endpoint:** `https://cosmos-alta-qa-001.documents.azure.com:443/`  
**Total Containers:** 12  
**Partition Key Strategy:** Mixed (see each container)

---

## 🗂️ Container Schemas

### 1. **alta_logs**
**Purpose:** Centralized application logging  
**Partition Key:** Not explicitly set (cross-partition queries enabled)  
**Document Type:** `alta_logs`

#### Document Structure
```json
{
  "id": "UUID (string)",
  "type": "alta_logs",
  "timestamp": "ISO 8601 UTC datetime string",
  "log_date": "YYYY-MM-DD (string)",
  "level": "INFO|WARNING|ERROR|DEBUG (string)",
  "message": "Log message (string)",
  "data": "Additional data (object/array or null)",
  "user_name": "Username (string or null)"
}
```

**Field Types:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID string | Yes | Primary key |
| type | string | Yes | Fixed: "alta_logs" |
| timestamp | ISO string | Yes | UTC timezone |
| log_date | date string | Yes | Used for partitioning queries |
| level | string | Yes | INFO, WARNING, ERROR, DEBUG |
| message | string | Yes | Log message text |
| data | object/array | No | Structured data payload |
| user_name | string | No | Associated user (null if system) |

---

### 2. **alta_filters**
**Purpose:** Modifier/filter definitions for translation refinement  
**Partition Key:** `__counter__` (for counter document), unique partition for data  
**Document Types:** `alta_filters`, `counter_filter_id`

#### Data Document Structure
```json
{
  "id": "UUID (string)",
  "type": "alta_filters",
  "filter_id": "integer",
  "modifier": "string",
  "value": "string",
  "system_prompt": "string",
  "user_prompt": "string",
  "created_by": "string or null",
  "created_at": "ISO 8601 UTC datetime string",
  "sequence": "integer"
}
```

**Field Types:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID string | Yes | Primary key |
| type | string | Yes | Fixed: "alta_filters" |
| filter_id | integer | Yes | Unique identifier (auto-increment) |
| modifier | string | Yes | Modifier name (e.g., "tone", "domain") |
| value | string | Yes | Modifier value |
| system_prompt | string | Yes | System prompt template |
| user_prompt | string | Yes | User prompt template |
| created_by | string | No | User who created filter |
| created_at | ISO string | Yes | Creation timestamp |
| sequence | integer | Yes | Order sequence |

#### Counter Document (for auto-increment)
```json
{
  "id": "counter_filter_id",
  "type": "counter",
  "partition_key": "__counter__",
  "value": "integer (current counter value)"
}
```

---

### 3. **contextsense_core_prompt**
**Purpose:** Store system prompts for context refinement  
**Partition Key:** `__counter__` (for counter), unique partition for data  
**Document Types:** `contextsense_core_prompt`, `counter_core_prompt_id`

#### Data Document Structure
```json
{
  "id": "integer (as string)",
  "type": "contextsense_core_prompt",
  "core_prompt_id": "integer",
  "prompt": "string",
  "created_by": "string or null",
  "created_at": "ISO 8601 UTC datetime string"
}
```

**Field Types:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | string (integer) | Yes | Primary key = core_prompt_id |
| type | string | Yes | Fixed: "contextsense_core_prompt" |
| core_prompt_id | integer | Yes | Unique identifier (auto-increment) |
| prompt | string | Yes | System prompt text (LLM instruction) |
| created_by | string | No | Creator user identifier |
| created_at | ISO string | Yes | Creation timestamp |

#### Counter Document
```json
{
  "id": "counter_core_prompt_id",
  "partition_key": "__counter__",
  "value": "integer"
}
```

---

### 4. **contextsense**
**Purpose:** Logs for context sense refinement operations (LLM refinements)  
**Partition Key:** Cross-partition (enable cross-partition queries)  
**Document Type:** `contextsense`

#### Document Structure
```json
{
  "id": "UUID (string)",
  "type": "contextsense",
  "user_id": "integer",
  "core_system_prompt_id": "integer",
  "translated_text": "string",
  "source_text": "string",
  "source_language": "string",
  "target_language": "string",
  "refined_text": "string",
  "explanation": "string",
  "user_context_id": "integer or null",
  "user_context_value": "string or null",
  "user_tone_id": "integer or null",
  "user_tone_value": "string or null",
  "user_domain_id": "integer or null",
  "user_domain_value": "string or null",
  "user_coherence_id": "integer or null",
  "user_coherence_value": "string or null",
  "user_audience_id": "integer or null",
  "user_audience_value": "string or null",
  "timestamp": "ISO 8601 UTC datetime string"
}
```

**Field Types:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID string | Yes | Primary key |
| type | string | Yes | Fixed: "contextsense" |
| user_id | integer | Yes | User identifier |
| core_system_prompt_id | integer | Yes | Reference to core prompt |
| translated_text | string | Yes | Original translation |
| source_text | string | Yes | Original source text |
| source_language | string | Yes | Language code |
| target_language | string | Yes | Language code |
| refined_text | string | Yes | LLM refined output |
| explanation | string | Yes | Refinement explanation from LLM |
| user_context_id | integer | No | Context modifier ID |
| user_context_value | string | No | Context modifier value |
| user_tone_id | integer | No | Tone modifier ID |
| user_tone_value | string | No | Tone modifier value |
| user_domain_id | integer | No | Domain modifier ID |
| user_domain_value | string | No | Domain modifier value |
| user_coherence_id | integer | No | Coherence modifier ID |
| user_coherence_value | string | No | Coherence modifier value |
| user_audience_id | integer | No | Audience modifier ID |
| user_audience_value | string | No | Audience modifier value |
| timestamp | ISO string | Yes | Operation timestamp |

---

### 5. **user_login_log**
**Purpose:** Track user login sessions  
**Partition Key:** `counter_login_session_id` (for counter), unique partition for data  
**Document Types:** `user_login_log`, `counter_login_session_id`

#### Data Document Structure
```json
{
  "id": "UUID (string)",
  "type": "user_login_log",
  "user": "string",
  "login_session_id": "integer",
  "login_date_and_time": "ISO 8601 UTC datetime string",
  "domain_name": "string or null"
}
```

**Field Types:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID string | Yes | Primary key |
| type | string | Yes | Fixed: "user_login_log" |
| user | string | Yes | Username |
| login_session_id | integer | Yes | Unique session ID (auto-increment) |
| login_date_and_time | ISO string | Yes | Login timestamp (UTC) |
| domain_name | string | No | Domain/tenant identifier |

#### Counter Document
```json
{
  "id": "counter_login_session_id",
  "partition_key": "counter_login_session_id",
  "value": "integer"
}
```

---

### 6. **user_text_trans_log**
**Purpose:** Log all text translation operations  
**Partition Key:** `__counter__` (for counter), cross-partition for queries  
**Document Types:** `user_text_trans_log`, `counter_log_id`

#### Data Document Structure
```json
{
  "id": "UUID (string)",
  "type": "user_text_trans_log",
  "user": "string",
  "source_text": "string",
  "translated_text": "string",
  "source_language": "string",
  "target_language": "string",
  "billed_characters": "string or null",
  "vendor": "string",
  "date_and_time": "ISO 8601 Eastern timezone datetime string",
  "log_id": "integer",
  "refinement_used": "boolean",
  "login_session_id": "integer or null",
  "domain_name": "string or null"
}
```

**Field Types:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID string | Yes | Primary key |
| type | string | Yes | Fixed: "user_text_trans_log" |
| user | string | Yes | Username |
| source_text | string | Yes | Original text to translate |
| translated_text | string | Yes | Translated result |
| source_language | string | Yes | Source language code |
| target_language | string | Yes | Target language code |
| billed_characters | string | No | Character count for billing |
| vendor | string | Yes | Vendor name (Azure, DeepL, etc.) |
| date_and_time | ISO string | Yes | Timestamp (Eastern timezone) |
| log_id | integer | Yes | Unique log ID (auto-increment) |
| refinement_used | boolean | Yes | Whether context sense refinement was applied |
| login_session_id | integer | No | Session reference |
| domain_name | string | No | Domain/tenant identifier |

#### Counter Document
```json
{
  "id": "counter_log_id",
  "partition_key": "__counter__",
  "value": "integer"
}
```

---

### 7. **user_docu_trans_log**
**Purpose:** Log all document translation operations  
**Partition Key:** `__counter__` (for counter), cross-partition for queries  
**Document Types:** `user_docu_trans_log`, `counter_log_id`

#### Data Document Structure
```json
{
  "id": "UUID (string)",
  "type": "user_docu_trans_log",
  "user": "string",
  "document_name": "string",
  "source_language": "string",
  "target_language": "string",
  "billed_characters": "integer or null",
  "size_of_the_document": "integer or null",
  "vendor": "string",
  "date_and_time": "ISO 8601 Eastern timezone datetime string",
  "log_id": "integer",
  "glossary_filename": "string or null",
  "login_session_id": "integer or null",
  "domain_name": "string or null"
}
```

**Field Types:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID string | Yes | Primary key |
| type | string | Yes | Fixed: "user_docu_trans_log" |
| user | string | Yes | Username |
| document_name | string | Yes | Filename of document |
| source_language | string | Yes | Source language code |
| target_language | string | Yes | Target language code |
| billed_characters | integer | No | Character count for billing |
| size_of_the_document | integer | No | Document size in bytes |
| vendor | string | Yes | Translation vendor |
| date_and_time | ISO string | Yes | Timestamp (Eastern timezone) |
| log_id | integer | Yes | Unique log ID (auto-increment) |
| glossary_filename | string | No | Custom glossary filename used |
| login_session_id | integer | No | Session reference |
| domain_name | string | No | Domain/tenant identifier |

#### Counter Document
```json
{
  "id": "counter_log_id",
  "partition_key": "__counter__",
  "value": "integer"
}
```

---

### 8. **user_feedback**
**Purpose:** Store user feedback and suggestions  
**Partition Key:** Cross-partition (enable cross-partition queries)  
**Document Type:** `user_feedback`

#### Document Structure
```json
{
  "id": "UUID (string)",
  "type": "user_feedback",
  "user": "string",
  "feedback": "string",
  "feedback_date_and_time": "ISO 8601 Eastern timezone datetime string",
  "login_session_id": "integer or null"
}
```

**Field Types:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID string | Yes | Primary key |
| type | string | Yes | Fixed: "user_feedback" |
| user | string | Yes | Username providing feedback |
| feedback | string | Yes | Feedback text content |
| feedback_date_and_time | ISO string | Yes | When feedback was submitted |
| login_session_id | integer | No | Associated login session |

---

### 9. **settings**
**Purpose:** Azure Translator configuration storage  
**Partition Key:** Not explicitly set  
**Document Type:** `settings`

#### Document Structure
```json
{
  "id": "UUID or configuration key (string)",
  "type": "settings",
  "setting_name": "string",
  "setting_value": "string or object",
  "created_at": "ISO 8601 datetime string or null",
  "updated_at": "ISO 8601 datetime string or null"
}
```

**Field Types:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | string | Yes | Primary key |
| type | string | Yes | Fixed: "settings" |
| setting_name | string | Yes | Configuration name |
| setting_value | string/object | Yes | Configuration value |
| created_at | ISO string | No | Creation timestamp |
| updated_at | ISO string | No | Last update timestamp |

---

### 10. **deepl_settings**
**Purpose:** DeepL API credential and configuration storage  
**Partition Key:** Not explicitly set  
**Document Type:** `deepl_settings`

#### Document Structure
```json
{
  "id": "UUID or admin ID (string)",
  "type": "deepl_settings",
  "admin_id": "string or integer",
  "api_key": "string (encrypted in practice)",
  "api_type": "string",
  "created_at": "ISO 8601 datetime string",
  "updated_at": "ISO 8601 datetime string or null"
}
```

**Field Types:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | string | Yes | Primary key |
| type | string | Yes | Fixed: "deepl_settings" |
| admin_id | string/integer | Yes | Administrator identifier |
| api_key | string | Yes | DeepL API key |
| api_type | string | Yes | API type identifier |
| created_at | ISO string | Yes | Creation timestamp |
| updated_at | ISO string | No | Last update timestamp |

---

### 11. **alta_var_settings**
**Purpose:** Store token quotas and limits per user/domain  
**Partition Key:** Cross-partition (enable cross-partition queries)  
**Document Type:** `alta_var_settings`

#### Document Structure
```json
{
  "id": "UUID (string)",
  "type": "alta_var_settings",
  "user": "string",
  "variable_name": "string",
  "variable_value": "string or integer",
  "item": "string or integer",
  "date_updated": "ISO 8601 datetime string"
}
```

**Field Types:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID string | Yes | Primary key |
| type | string | Yes | Fixed: "alta_var_settings" |
| user | string | Yes | User identifier |
| variable_name | string | Yes | Variable name (e.g., "token_limit") |
| variable_value | string/integer | Yes | Variable value |
| item | string/integer | No | Item identifier/type |
| date_updated | ISO string | Yes | Last update timestamp |

---

### 12. **alta_reports_access**
**Purpose:** Control access to reports by user/domain  
**Partition Key:** Cross-partition (enable cross-partition queries)  
**Document Type:** `alta_reports_access`

#### Document Structure
```json
{
  "id": "UUID (string)",
  "type": "alta_reports_access",
  "access_id": "integer",
  "user": "string",
  "domain_name": "string",
  "report_name": "string",
  "access_level": "string",
  "created_at": "ISO 8601 datetime string",
  "updated_at": "ISO 8601 datetime string or null"
}
```

**Field Types:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID string | Yes | Primary key |
| type | string | Yes | Fixed: "alta_reports_access" |
| access_id | integer | Yes | Unique access record ID |
| user | string | Yes | Username |
| domain_name | string | Yes | Domain/tenant identifier |
| report_name | string | Yes | Report name |
| access_level | string | Yes | Access level (e.g., "read", "admin") |
| created_at | ISO string | Yes | Creation timestamp |
| updated_at | ISO string | No | Last update timestamp |

---

## 🔑 Key Design Patterns

### 1. **Document ID (Primary Key)**
- **Type:** Always `UUID string` (except contextsense_core_prompt which uses integer)
- **Generated:** Via `str(uuid.uuid4())` in Python
- **Purpose:** Unique identifier for each document

### 2. **Type Field**
- **Purpose:** Document classification within container
- **Values:** Match container name (e.g., "alta_logs", "user_login_log")
- **Usage:** Query filtering, application logic

### 3. **Timestamp Fields**
- **Formats Used:**
  - UTC ISO 8601: `"2024-09-08T12:34:56.789123+00:00"`
  - Eastern timezone: `"2024-09-08T08:34:56.789123-04:00"`
- **Fields:** `timestamp`, `date_and_time`, `created_at`, `login_date_and_time`
- **Generation:** `datetime.now(timezone.utc).isoformat()` or `pytz` for Eastern

### 4. **Auto-Increment Pattern**
**Containers with auto-increment:**
- `alta_filters` → `filter_id`
- `contextsense_core_prompt` → `core_prompt_id`
- `user_login_log` → `login_session_id`
- `user_text_trans_log` → `log_id`
- `user_docu_trans_log` → `log_id`

**Implementation:**
```json
{
  "id": "counter_<field_name>",
  "partition_key": "__counter__",
  "value": "integer"
}
```

**Access Method:**
```python
counter = container.read_item(item='counter_filter_id', partition_key='__counter__')
counter['value'] += 1
# Update with etag for concurrency control
```

### 5. **Partition Strategy**
- **Counter documents:** Use partition key `__counter__`
- **Data documents:** Either match container name or use cross-partition queries
- **Query mode:** `enable_cross_partition_query=True` for most read operations

---

## 📊 Data Types Summary

| Type | Usage | Examples |
|------|-------|----------|
| UUID string | Primary identifiers | `"a1b2c3d4-e5f6-7890-abcd-ef1234567890"` |
| Integer | Counters, IDs, sizes | `1`, `100`, `5000` |
| String | Text fields, codes | `"user@domain.com"`, `"en"`, `"fr"` |
| ISO datetime | Timestamps | `"2024-09-08T12:34:56.789123+00:00"` |
| Boolean | Flags | `true`, `false` |
| Object/Array | Complex data | `{"key": "value"}`, `[1, 2, 3]` |
| null | Optional fields | Missing or empty values |

---

## 🔗 Entity Relationships

```
user_login_log (login_session_id)
    ↓
user_text_trans_log (login_session_id)
user_docu_trans_log (login_session_id)
user_feedback (login_session_id)

alta_filters (filter_id)
    ↓
contextsense (user_*_id, user_*_value)

contextsense_core_prompt (core_prompt_id)
    ↓
contextsense (core_system_prompt_id)

alta_reports_access
    → user, domain_name

alta_var_settings
    → user, variable_name
```

---

## 💾 Database Connection Configuration

```python
# Connection details from .env
COSMOS_ENDPOINT=https://cosmos-alta-qa-001.documents.azure.com:443/
COSMOS_KEY=<primary-key>
COSMOS_DB_NAME=cosmos-alta-qa-001
```

**Python connection example:**
```python
from azure.cosmos import CosmosClient

cosmos_client = CosmosClient(
    os.getenv('COSMOS_ENDPOINT'),
    os.getenv('COSMOS_KEY')
)
database = cosmos_client.get_database_client(os.getenv('COSMOS_DB_NAME'))
container = database.get_container_client('container_name')
```

---

## 📝 Notes for Database Creator/Administrator

1. **RU (Request Units) Provisioning:** Allocate sufficient RU based on expected throughput
2. **Auto-increment Implementation:** Uses counter documents with ETag-based optimistic concurrency control
3. **Timezone Handling:** Mix of UTC and Eastern timezone - ensure application handles conversions
4. **Cross-partition Queries:** Enable for containers without explicit partition key
5. **TTL (Time to Live):** Consider implementing TTL on logs containers for data retention policies
6. **Backup Strategy:** Configure Cosmos DB automatic backup (geo-redundant)
7. **Security:** API keys should be stored in Azure Key Vault, not in .env files for production


