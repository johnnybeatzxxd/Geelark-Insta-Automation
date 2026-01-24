# migrate.py
from database import db, DeviceLog

try:
    print("--- STARTING MIGRATION ---")
    db.connect(reuse_if_open=True)
    # create_tables is safe (checks if exists)
    db.create_tables([DeviceLog])
    print('✅ Migration complete: DeviceLog table created (if it didn\'t exist)')
except Exception as e:
    print(f'❌ Migration error: {e}')