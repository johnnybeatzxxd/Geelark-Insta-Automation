# migrate.py
from database import db, Account

try:
    print("--- STARTING MIGRATION ---")
    db.connect(reuse_if_open=True)
    
    # Add stream_url column to Account table if it doesn't exist
    cursor = db.execute_sql("PRAGMA table_info(account)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'stream_url' not in columns:
        print("Adding 'stream_url' column to Account table...")
        db.execute_sql("ALTER TABLE account ADD COLUMN stream_url VARCHAR(255) NULL")
        print('✅ Migration complete: stream_url column added to Account table')
    else:
        print('✅ stream_url column already exists, skipping migration')
        
except Exception as e:
    print(f'❌ Migration error: {e}')