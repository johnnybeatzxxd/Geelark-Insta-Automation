from peewee import *
import datetime
import os

# Create file-based DB
db = SqliteDatabase('instagram_actions.db')

class BaseModel(Model):
    class Meta:
        database = db

class Target(BaseModel):
    username = CharField(unique=True)
    status = CharField(default='pending') # pending, followed, failed, ignored
    source = CharField(null=True)         # e.g. "manual_list"
    added_date = DateTimeField(default=datetime.datetime.now)
    last_action_date = DateTimeField(null=True)

def initialize_db():
    db.connect()
    db.create_tables([Target])

def import_targets_from_file(filepath):
    if not os.path.exists(filepath): return 0
    count = 0
    with open(filepath, 'r') as f:
        users = [line.strip() for line in f if line.strip()]
    
    for user in users:
        try:
            Target.create(username=user, source="file_import")
            count += 1
        except IntegrityError:
            pass # Already exists
    return count

def get_pending_batch(limit=15):
    # Get oldest pending users first
    return list(Target.select().where(Target.status == 'pending').limit(limit))

def update_target_status(username, new_status):
    Target.update(
        status=new_status, 
        last_action_date=datetime.datetime.now()
    ).where(Target.username == username).execute()

# Auto-init on import
if not os.path.exists('instagram_actions.db'):
    initialize_db()
