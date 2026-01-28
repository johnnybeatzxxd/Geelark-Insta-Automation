# migrate_mode.py
from peewee import SqliteDatabase
from database import DB_NAME

db = SqliteDatabase(DB_NAME)

def migrate():
    print("Adding task_mode to Account table...")
    db.connect()
    try:
        # Default to 'follow' so existing bots don't break
        db.execute_sql("ALTER TABLE account ADD COLUMN task_mode TEXT DEFAULT 'follow'")
        print("Success.")
    except Exception as e:
        print(f"Skipped: {e}")
    db.close()

# migrate_db.py
import json
from database import SystemConfig, DEFAULT_WARMUP_STRATEGY

def migrate_config():
    print("Migrating Config JSON...")
    try:
        conf = SystemConfig.get_or_none(SystemConfig.key == 'session_config')
        if conf:
            current_config = json.loads(conf.value)
            
            # Check if key exists
            if 'warmup_strategy' not in current_config:
                current_config['warmup_strategy'] = DEFAULT_WARMUP_STRATEGY
                print("[UPDATE] Added 'warmup_strategy' to config.")
                
                conf.value = json.dumps(current_config)
                conf.save()
            else:
                print("[SKIP] 'warmup_strategy' already exists.")
    except Exception as e:
        print(f"Error: {e}")

def migrate_warmup_day():
    print("Adding 'warmup_day' to Account table...")
    db.connect()
    try:
        # Default to Day 1
        db.execute_sql("ALTER TABLE account ADD COLUMN warmup_day INTEGER DEFAULT 1")
        print("Success.")
    except Exception as e:
        print(f"Skipped: {e}")
    db.close()

if __name__ == "__main__":
    migrate()
    migrate_config()
    migrate_warmup_day()
