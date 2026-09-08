# PostgreSQL → Cosmos DB Schema Migration Mapping
## Complete Table Comparison & Format Changes

---

## 📊 Overview

**Migration Type:** PostgreSQL (Relational) → Cosmos DB NoSQL (Document-based)

**Key Differences:**
- PostgreSQL uses rigid schemas with foreign keys
- Cosmos DB uses flexible JSON documents with no enforced relationships
- Table names → Container names (mostly same)
- Rows → Documents with `type` field for classification
- Sequential IDs → UUID primary keys + separate counter documents for auto-increment

---

## 🗂️ Table-by-Table Mapping

### 1. **logs** → `alta_logs`

#### PostgreSQL Schema
```sql
CREATE TABLE logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    level VARCHAR(50),
    log TEXT,
    data JSON,
    session_id UUID,
    user_name VARCHAR(255)
);
```

#### Cosmos DB Schema
```json
{
  "id": "UUID (string)",
  "type": "alta_logs",
  "timestamp": "ISO 8601 UTC",
  "log_date": "YYYY-MM-DD",
  "level": "INFO|WARNING|ERROR|DEBUG",
  "message": "string",
  "data": "object/array or null",
  "user_name": "string or null"
}
```

**Changes:**
- ❌ `id SERIAL` → ✅ `id UUID`
- ✅ `timestamp` stays same (ISO format now)
- ✅ `level` stays same
- ❌ `log` (column name) → ✅ `message` (field name)
- ✅ `data` stays JSON
- ✅ `session_id` stays
- ✅ `user_name` stays

---

### 2. **alta_filters** → `alta_filters`

#### PostgreSQL Schema
```sql
CREATE TABLE alta_filters (
    id SERIAL PRIMARY KEY,
    filter_id SERIAL UNIQUE,
    modifier VARCHAR(255),
    value VARCHAR(255),
    system_prompt TEXT,
    user_prompt TEXT,
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sequence INTEGER
);
```

#### Cosmos DB Schema
```json
{
  "id": "UUID (string)",
  "type": "alta_filters",
  "filter_id": "integer (auto-increment)",
  "modifier": "string",
  "value": "string",
  "system_prompt": "string",
  "user_prompt": "string",
  "created_by": "string or null",
  "created_at": "ISO 8601 UTC",
  "sequence": "integer"
}
```

**Separate Counter Document:**
```json
{
  "id": "counter_filter_id",
  "partition_key": "__counter__",
  "value": "integer (current counter)"
}
```

**Changes:**
- ❌ `id SERIAL PRIMARY KEY` → ✅ `id UUID` (for uniqueness)
- ✅ `filter_id` now stored as regular field (auto-increment via counter doc)
- ✅ All other fields same
- ➕ Added `type: "alta_filters"` for document classification

---

### 3. **contextsense_core_prompt** → `contextsense_core_prompt`

#### PostgreSQL Schema
```sql
CREATE TABLE contextsense_core_prompt (
    core_prompt_id SERIAL PRIMARY KEY,
    prompt TEXT,
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Cosmos DB Schema
```json
{
  "id": "string (core_prompt_id as string)",
  "type": "contextsense_core_prompt",
  "core_prompt_id": "integer",
  "prompt": "string",
  "created_by": "string or null",
  "created_at": "ISO 8601 UTC"
}
```

**Counter Document:**
```json
{
  "id": "counter_core_prompt_id",
  "partition_key": "__counter__",
  "value": "integer"
}
```

**Changes:**
- ❌ `core_prompt_id SERIAL PRIMARY KEY` → ✅ `id` is string (conversion of core_prompt_id)
- ✅ All other fields same
- ➕ Added `type` field

---

### 4. **contextsense** → `contextsense`

#### PostgreSQL Schema
```sql
CREATE TABLE contextsense (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    core_system_prompt_id INTEGER,
    translated_text TEXT,
    source_text TEXT,
    source_language VARCHAR(10),
    target_language VARCHAR(10),
    refined_text TEXT,
    explanation TEXT,
    user_context_id INTEGER,
    user_context_value VARCHAR(255),
    user_tone_id INTEGER,
    user_tone_value VARCHAR(255),
    user_domain_id INTEGER,
    user_domain_value VARCHAR(255),
    user_coherence_id INTEGER,
    user_coherence_value VARCHAR(255),
    user_audience_id INTEGER,
    user_audience_value VARCHAR(255),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Cosmos DB Schema
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
  "timestamp": "ISO 8601 UTC"
}
```

**Changes:**
- ❌ `id SERIAL` → ✅ `id UUID`
- ✅ All other fields: same structure, just stored as JSON properties

---

### 5. **user_login_log** → `user_login_log`

#### PostgreSQL Schema
```sql
CREATE TABLE user_login_log (
    id SERIAL PRIMARY KEY,
    "user" VARCHAR(255),
    login_session_id SERIAL,
    login_date_and_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    domain_name VARCHAR(255)
);
```

#### Cosmos DB Schema
```json
{
  "id": "UUID (string)",
  "type": "user_login_log",
  "user": "string",
  "login_session_id": "integer (auto-increment)",
  "login_date_and_time": "ISO 8601 UTC",
  "domain_name": "string or null"
}
```

**Counter Document:**
```json
{
  "id": "counter_login_session_id",
  "partition_key": "counter_login_session_id",
  "value": "integer"
}
```

**Changes:**
- ❌ `id SERIAL` → ✅ `id UUID`
- ✅ `user` field stays same (note: quoted in SQL because it's reserved word)
- ✅ `login_session_id` now managed via counter document
- ✅ Timestamps same (ISO format)
- ✅ `domain_name` same

---

### 6. **user_text_trans_log** → `user_text_trans_log`

#### PostgreSQL Schema
```sql
CREATE TABLE user_text_trans_log (
    id SERIAL PRIMARY KEY,
    "user" VARCHAR(255),
    source_text TEXT,
    translated_text TEXT,
    source_language VARCHAR(10),
    target_language VARCHAR(10),
    billed_characters INTEGER,
    vendor VARCHAR(50),
    date_and_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    log_id SERIAL,
    refinement_used BOOLEAN,
    login_session_id INTEGER,
    domain_name VARCHAR(255)
);
```

#### Cosmos DB Schema
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
  "date_and_time": "ISO 8601 Eastern timezone",
  "log_id": "integer (auto-increment)",
  "refinement_used": "boolean",
  "login_session_id": "integer or null",
  "domain_name": "string or null"
}
```

**Counter Document:**
```json
{
  "id": "counter_log_id",
  "partition_key": "__counter__",
  "value": "integer"
}
```

**Changes:**
- ❌ `id SERIAL` → ✅ `id UUID`
- ✅ All other fields: same structure
- 🌍 `date_and_time`: NOW uses Eastern timezone (was UTC in PostgreSQL)
- ✅ `log_id` managed via counter document
- ❌ `billed_characters` changed from INTEGER → STRING (or null)

---

### 7. **user_docu_trans_log** → `user_docu_trans_log`

#### PostgreSQL Schema
```sql
CREATE TABLE user_docu_trans_log (
    id SERIAL PRIMARY KEY,
    "user" VARCHAR(255),
    document_name VARCHAR(255),
    source_language VARCHAR(10),
    target_language VARCHAR(10),
    billed_characters INTEGER,
    size_of_the_document INTEGER,
    vendor VARCHAR(50),
    date_and_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    log_id SERIAL,
    glossary_filename VARCHAR(255),
    login_session_id INTEGER,
    domain_name VARCHAR(255)
);
```

#### Cosmos DB Schema
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
  "date_and_time": "ISO 8601 Eastern timezone",
  "log_id": "integer (auto-increment)",
  "glossary_filename": "string or null",
  "login_session_id": "integer or null",
  "domain_name": "string or null"
}
```

**Counter Document:**
```json
{
  "id": "counter_log_id",
  "partition_key": "__counter__",
  "value": "integer"
}
```

**Changes:**
- ❌ `id SERIAL` → ✅ `id UUID`
- ✅ All other fields: same structure
- 🌍 `date_and_time`: NOW uses Eastern timezone
- ✅ `log_id` managed via counter document

---

### 8. **user_feedback** → `user_feedback`

#### PostgreSQL Schema
```sql
CREATE TABLE user_feedback (
    id SERIAL PRIMARY KEY,
    "user" VARCHAR(255),
    feedback TEXT,
    feedback_date_and_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    login_session_id INTEGER
);
```

#### Cosmos DB Schema
```json
{
  "id": "UUID (string)",
  "type": "user_feedback",
  "user": "string",
  "feedback": "string",
  "feedback_date_and_time": "ISO 8601 Eastern timezone",
  "login_session_id": "integer or null"
}
```

**Changes:**
- ❌ `id SERIAL` → ✅ `id UUID`
- ✅ All other fields: same
- 🌍 `feedback_date_and_time`: NOW uses Eastern timezone

---

### 9. **settings** → `settings`

#### PostgreSQL Schema
```sql
CREATE TABLE settings (
    id SERIAL PRIMARY KEY,
    admin_id VARCHAR(255),
    "key" VARCHAR(255),
    text_translation_endpoint VARCHAR(500),
    document_translation_endpoint VARCHAR(500),
    region VARCHAR(100),
    storage_connection_string VARCHAR(1000)
);
```

#### Cosmos DB Schema
```json
{
  "id": "UUID or config key (string)",
  "type": "settings",
  "setting_name": "string",
  "setting_value": "string or object",
  "created_at": "ISO 8601 or null",
  "updated_at": "ISO 8601 or null"
}
```

**Changes:**
- ❌ Multiple columns → ✅ Flexible key-value structure
- ❌ `admin_id`, `key` → ✅ `setting_name`, `setting_value`
- ➕ Added timestamps for audit trail

---

### 10. **deepl_settings** → `deepl_settings`

#### PostgreSQL Schema
```sql
CREATE TABLE deepl_settings (
    id SERIAL PRIMARY KEY,
    admin_id VARCHAR(255),
    api_key VARCHAR(500),
    api_type VARCHAR(50)
);
```

#### Cosmos DB Schema
```json
{
  "id": "UUID or admin ID (string)",
  "type": "deepl_settings",
  "admin_id": "string or integer",
  "api_key": "string (encrypted)",
  "api_type": "string",
  "created_at": "ISO 8601",
  "updated_at": "ISO 8601 or null"
}
```

**Changes:**
- ❌ `id SERIAL` → ✅ `id` can be UUID or admin ID
- ✅ `admin_id`, `api_key`, `api_type` same
- ➕ Added audit timestamps

---

### 11. **alta_var_settings** → `alta_var_settings`

#### PostgreSQL Schema
```sql
CREATE TABLE alta_var_settings (
    id SERIAL PRIMARY KEY,
    "user" VARCHAR(255),
    variable_name VARCHAR(255),
    variable_value VARCHAR(255),
    item VARCHAR(255),
    date_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Cosmos DB Schema
```json
{
  "id": "UUID (string)",
  "type": "alta_var_settings",
  "user": "string",
  "variable_name": "string",
  "variable_value": "string or integer",
  "item": "string or integer or null",
  "date_updated": "ISO 8601 UTC"
}
```

**Changes:**
- ❌ `id SERIAL` → ✅ `id UUID`
- ✅ All other fields: same

---

### 12. **alta_reports_access** → `alta_reports_access`

#### PostgreSQL Schema
```sql
CREATE TABLE alta_reports_access (
    id SERIAL PRIMARY KEY,
    access_id SERIAL,
    "user" VARCHAR(255),
    domain_name VARCHAR(255),
    report_name VARCHAR(255),
    access_level VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### Cosmos DB Schema
```json
{
  "id": "UUID (string)",
  "type": "alta_reports_access",
  "access_id": "integer",
  "user": "string",
  "domain_name": "string",
  "report_name": "string",
  "access_level": "string",
  "created_at": "ISO 8601 UTC",
  "updated_at": "ISO 8601 UTC or null"
}
```

**Changes:**
- ❌ `id SERIAL` → ✅ `id UUID`
- ✅ All other fields: same

---

## 📋 Key Migration Patterns

### 1. **Primary Keys**
| PostgreSQL | Cosmos DB | Reason |
|-----------|-----------|--------|
| `id SERIAL` | `id UUID string` | NoSQL best practice; UUIDs prevent collisions |
| Integer auto-increment | Counter documents | Emulates SERIAL with optimistic concurrency control |

### 2. **Auto-Increment Pattern**
**PostgreSQL:**
```sql
CREATE TABLE table_name (
    id SERIAL PRIMARY KEY
);
```

**Cosmos DB:**
```python
# Data document
{"id": "UUID", "filter_id": 123, ...}

# Separate counter document
{"id": "counter_filter_id", "partition_key": "__counter__", "value": 123}

# On insert:
counter = container.read_item(item='counter_filter_id', partition_key='__counter__')
counter['value'] += 1
container.replace_item(counter, etag=counter['_etag'])  # Optimistic concurrency
```

### 3. **Timestamps**
| PostgreSQL | Cosmos DB | Usage |
|-----------|-----------|-------|
| `TIMESTAMP DEFAULT CURRENT_TIMESTAMP` | `ISO 8601 string` | Standardized format |
| UTC timezone | Mixed: UTC or Eastern | Depends on business logic |

### 4. **JSON Data**
| PostgreSQL | Cosmos DB | Change |
|-----------|-----------|--------|
| `data JSON` | `data object/array` | Stored natively in JSON |

### 5. **Null Handling**
| PostgreSQL | Cosmos DB | Note |
|-----------|-----------|------|
| `NULL` | `null` or field absent | Both allowed; field absence preferred in NoSQL |

### 6. **Foreign Keys**
| PostgreSQL | Cosmos DB | Change |
|-----------|-----------|--------|
| Enforced foreign keys | No enforced relationships | Manual referential integrity (via code) |

**Example:**
```python
# PostgreSQL
user_id = 123  # Must exist in users table

# Cosmos DB
{
  "id": "UUID",
  "user_id": 123,  # No validation at DB level; checked in application code
}
```

---

## ✅ Data Type Mapping

| PostgreSQL | Cosmos DB | Notes |
|-----------|-----------|-------|
| `SERIAL / INTEGER` | `integer` | Stored as JSON number |
| `VARCHAR(n)` | `string` | No length limit in JSON |
| `TEXT` | `string` | Both unlimited strings |
| `BOOLEAN` | `boolean` | JSON true/false |
| `TIMESTAMP` | `ISO 8601 string` | e.g., "2024-09-08T12:34:56+00:00" |
| `JSON` | `object/array` | Native JSON in Cosmos |
| `UUID` | `string` | Stored as UUID string representation |
| `NULL` | `null` or omitted | JSON null or field absence |

---

## 🚀 Migration Considerations

### What Changed:
1. ✅ **Table names** → Mostly same (logs → alta_logs)
2. ✅ **Column names** → Mostly same (log → message exception)
3. ✅ **Data types** → Simplified to JSON types
4. ✅ **Relationships** → No foreign keys (application-level enforcement)
5. ✅ **Indexes** → Partition keys instead of traditional indexes
6. ✅ **Sequences** → Counter documents pattern

### What Stayed Same:
- ✅ Field semantics and business logic
- ✅ Data values (with format conversions)
- ✅ Multi-tenant capability via `domain_name`
- ✅ Audit trails via `created_at`, `updated_at`

### Performance Impact:
- ✅ Cross-partition queries faster with Cosmos
- ✅ Point lookups by `id` same speed
- ✅ Range queries on `timestamp` now require index on that field
- ✅ Joins replaced by denormalization (less efficient sometimes)

---

## 🔄 Backward Compatibility

**For code migrating from PostgreSQL to Cosmos:**
- ✅ Same business logic works with minimal changes
- ✅ SQL queries → Cosmos Query Language (SQL-like syntax for JSON)
- ✅ `psycopg2` → `azure.cosmos.CosmosClient`
- ✅ Transaction handling differs (no ACID guarantees in NoSQL)

---

## 📝 Migration Status

| Container | Status | Notes |
|-----------|--------|-------|
| alta_logs | ✅ MIGRATED | Fully functional, logging works |
| alta_filters | ✅ MIGRATED | Auto-increment via counter works |
| contextsense_core_prompt | ✅ MIGRATED | Prompts stored correctly |
| contextsense | ✅ MIGRATED | LLM refinement logs working |
| user_login_log | ✅ MIGRATED | Session tracking works |
| user_text_trans_log | ✅ MIGRATED | Text translation audit trail complete |
| user_docu_trans_log | ✅ MIGRATED | Document translation audit trail complete |
| user_feedback | ✅ MIGRATED | Feedback collection working |
| settings | ✅ MIGRATED | Azure/DeepL settings stored |
| deepl_settings | ✅ MIGRATED | DeepL credentials stored |
| alta_var_settings | ✅ MIGRATED | Token quotas working |
| alta_reports_access | ✅ MIGRATED | Report access control working |

**Overall Status:** ✅ **100% MIGRATED - Production Ready**

---

**Document Generated:** 2024-09-08  
**Migration Completion:** Sept 3, 2024  
**Application:** Alta Translation Management System  
**Database:** PostgreSQL → Cosmos DB NoSQL
