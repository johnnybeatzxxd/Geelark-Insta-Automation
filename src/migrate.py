# migrate_db.py
import json
from peewee import SqliteDatabase
from database import DB_NAME, SystemConfig

db = SqliteDatabase(DB_NAME)

def run_migration():
    print(f"Connecting to {DB_NAME}...")
    db.connect()
    
    # 1. ADD COLUMNS TO ACCOUNT TABLE
    # SQLite allows adding columns via raw SQL
    try:
        db.execute_sql('ALTER TABLE account ADD COLUMN cached_2h_count INTEGER DEFAULT 0')
        print("[SUCCESS] Added 'cached_2h_count' column.")
    except Exception as e:
        print(f"[SKIP] 'cached_2h_count' likely exists: {e}")

    try:
        db.execute_sql('ALTER TABLE account ADD COLUMN cached_24h_count INTEGER DEFAULT 0')
        print("[SUCCESS] Added 'cached_24h_count' column.")
    except Exception as e:
        print(f"[SKIP] 'cached_24h_count' likely exists: {e}")

    # 2. UPDATE SESSION CONFIG JSON
    try:
        conf = SystemConfig.get_or_none(SystemConfig.key == 'session_config')
        if conf:
            current_config = json.loads(conf.value)
            
            # Add 'continuous_mode' if missing
            if 'continuous_mode' not in current_config:
                current_config['continuous_mode'] = True # Default to True (Old behavior)
                print("[UPDATE] Added 'continuous_mode=True' to session config.")
                
            # Update DB
            conf.value = json.dumps(current_config)
            conf.save()
            print("[SUCCESS] Config JSON updated.")
        else:
            print("[INFO] No session_config found in DB. Defaults will be used.")
            
    except Exception as e:
        print(f"[ERROR] updating config: {e}")

    db.close()
    print("Migration Complete.")

if __name__ == "__main__":
    run_migration()
