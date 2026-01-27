import json
from peewee import SqliteDatabase
from database import DB_NAME, SystemConfig

db = SqliteDatabase(DB_NAME)

def run_migration():
    print(f"Connecting to {DB_NAME}...")
    db.connect()

    # UPDATE SESSION CONFIG JSON
    try:
        conf = SystemConfig.get_or_none(SystemConfig.key == 'session_config')
        if conf:
            current_config = json.loads(conf.value)
            
            # Add 'max_concurrent_sessions' if missing
            if 'max_concurrent_sessions' not in current_config:
                current_config['max_concurrent_sessions'] = 5 # Default value
                print("[UPDATE] Added 'max_concurrent_sessions=5' to session config.")
                
                # Update DB
                conf.value = json.dumps(current_config)
                conf.save()
                print("[SUCCESS] Config JSON updated.")
            else:
                print("[INFO] 'max_concurrent_sessions' already exists in config.")
        else:
            print("[INFO] No session_config found in DB. Defaults will be used automatically.")
            
    except Exception as e:
        print(f"[ERROR] updating config: {e}")

    db.close()
    print("Migration Complete.")

if __name__ == "__main__":
    run_migration()
