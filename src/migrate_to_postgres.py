import os
from peewee import *
import datetime

# --- 1. SOURCE (SQLite) ---
sqlite_db = SqliteDatabase('instagram_farm.db')

# --- 2. DESTINATION (Postgres) ---
pg_db = PostgresqlDatabase(
    'instagram_farm',
    user='farm_user',
    password='farm_password_123',
    host='db', 
    port=5432
)

# --- 3. MODELS ---
class MigrationModel(Model):
    class Meta:
        database = None

class SystemConfig(MigrationModel):
    key = CharField(unique=True)
    value = TextField()

class Account(MigrationModel):
    device_id = CharField(primary_key=True)
    profile_name = CharField(null=True)
    is_enabled = BooleanField(default=False)
    runtime_status = CharField(default='STOPPED')
    status = CharField(default='active')
    daily_limit = IntegerField(default=100)
    created_at = DateTimeField(default=datetime.datetime.now)
    cooldown_until = DateTimeField(null=True)
    stream_url = TextField(null=True)
    task_mode = CharField(default='follow')
    warmup_day = IntegerField(default=1)
    cached_2h_count = IntegerField(default=0)
    cached_24h_count = IntegerField(default=0)

class Target(MigrationModel):
    username = CharField(unique=True)
    source = CharField(null=True)
    status = CharField(default='pending') 
    added_at = DateTimeField(default=datetime.datetime.now)

class Action(MigrationModel):
    # We use CharField for the IDs during migration to avoid FK lookup failures
    account_id = CharField() 
    target_id = CharField()
    action_type = CharField(default='follow') 
    result = CharField(default='success')
    timestamp = DateTimeField(default=datetime.datetime.now)

class SystemCommand(MigrationModel):
    command = CharField()
    target_id = CharField(null=True)
    status = CharField(default='pending')
    created_at = DateTimeField(default=datetime.datetime.now)
    executed_at = DateTimeField(null=True)

class DeviceLog(MigrationModel):
    device_id = CharField()
    device_name = CharField()
    message = TextField()
    level = CharField(default='INFO')
    timestamp = DateTimeField(default=datetime.datetime.now)
    is_sent = BooleanField(default=False)

def run_migration():
    print("--- STARTING FULL MIGRATION ---")
    
    try:
        sqlite_db.connect()
        pg_db.connect()
    except Exception as e:
        print(f"Connection Error: {e}")
        return

    # Tables to migrate in order
    tables = [SystemConfig, Account, Target, Action, SystemCommand]
    
    # 1. READ ALL DATA FROM SQLITE
    data_map = {}
    for model in tables:
        model._meta.database = sqlite_db
        print(f"Reading {model.__name__}...")
        try:
            data_map[model.__name__] = list(model.select().dicts())
        except:
            print(f"  ! Table {model.__name__} not found in SQLite. Skipping.")
            data_map[model.__name__] = []

    # 2. SANITIZE DATA
    print("Sanitizing data...")
    
    # Clean Accounts
    for acc in data_map['Account']:
        if acc.get('runtime_status') is None: acc['runtime_status'] = 'STOPPED'
        if acc.get('task_mode') is None: acc['task_mode'] = 'follow'
        acc.pop('reserved_targets', None) # Remove backrefs
        
    # Clean Targets (Clear old locks)
    for t in data_map['Target']:
        if t.get('status') == 'reserved': t['status'] = 'pending'
        t.pop('reserved_by', None)
        t.pop('reserved_at', None)

    # Clean Actions (Match ID naming for dict insert)
    for act in data_map['Action']:
        # Peewee .dicts() might return 'account' instead of 'account_id'
        if 'account' in act: act['account_id'] = act.pop('account')
        if 'target' in act: act['target_id'] = act.pop('target')

    # 3. WRITE TO POSTGRES
    print("Preparing Postgres Tables...")
    for model in tables:
        model._meta.database = pg_db
    
    pg_db.create_tables(tables, safe=True)

    with pg_db.atomic():
        for model in tables:
            data = data_map[model.__name__]
            if not data: continue
            
            print(f"Inserting {len(data)} rows into {model.__name__}...")
            # Use chunks of 100 to prevent memory spikes
            for i in range(0, len(data), 100):
                chunk = data[i:i+100]
                if model == SystemConfig:
                    model.insert_many(chunk).on_conflict_ignore().execute()
                elif model == Account:
                    model.insert_many(chunk).on_conflict_ignore().execute()
                elif model == Target:
                    model.insert_many(chunk).on_conflict_ignore().execute()

    print("--- FULL MIGRATION COMPLETE ---")
    sqlite_db.close()
    pg_db.close()

if __name__ == "__main__":
    run_migration()
