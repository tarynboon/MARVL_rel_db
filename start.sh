#!/bin/bash
set -e

DB="${DB_PATH:-/data/marvl.db}"
SCHEMA="/app/marvl_database_schema_v1.2.sql"

if [ ! -f "$DB" ]; then
    echo "No database found at $DB — initializing empty schema..."
    python3 -c "
import sqlite3, os
schema = open('$SCHEMA', 'r', encoding='utf-8').read()
os.makedirs(os.path.dirname('$DB'), exist_ok=True)
conn = sqlite3.connect('$DB')
conn.executescript(schema)
conn.close()
print('Schema initialized.')
"
fi

exec uvicorn api.main:app --host 0.0.0.0 --port 8000
