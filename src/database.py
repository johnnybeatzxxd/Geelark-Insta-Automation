import datetime
import os
from typing import List, Dict, Optional
from peewee import *

# --- DATABASE SETUP ---
DB_NAME = 'instagram_farm.db'
# We use WAL mode to allow the Manager and multiple Workers to write to the DB at the same time safely.
db = SqliteDatabase(DB_NAME, pragmas={'journal_mode': 'wal', 'foreign_keys': 1})

class BaseModel(Model):
    class Meta:
        database = db

# --- 1. SYSTEM CONFIG (Global Control) ---
class SystemConfig(BaseModel):
    key = CharField(unique=True)   # e.g., 'global_automation_status'
    value = CharField()            # 'ON' or 'OFF'

# --- 2. ACCOUNTS (The Workers) ---
class Account(BaseModel):
    device_id = CharField(primary_key=True)
    profile_name = CharField(null=True)
    
    # INPUT: The User's Switch
    is_enabled = BooleanField(default=False) 
    
    # Values: 'DISABLED', 'IDLE', 'RUNNING', 'COOLDOWN', 'NO_TARGETS'
    runtime_status = CharField(default='DISABLED') 
    
    status = CharField(default='active') # Cloud status (active/banned)
    daily_limit = IntegerField(default=100)
    created_at = DateTimeField(default=datetime.datetime.now)
    
    # HARD COOLDOWN: Account cannot run until this time (survives reboots)
    cooldown_until = DateTimeField(null=True)
    
    # Stream URL for remote viewing
    stream_url = CharField(null=True)

    cached_2h_count = IntegerField(default=0)
    cached_24h_count = IntegerField(default=0)

# --- 3. TARGETS (The Leads) ---
class Target(BaseModel):
    username = CharField(unique=True)
    source = CharField(null=True)
    
    # Life cycle: pending -> reserved -> completed (or failed)
    status = CharField(default='pending') 
    
    # The 'Lock' - which account is currently trying to follow this person
    reserved_by = ForeignKeyField(Account, backref='reserved_targets', null=True)
    reserved_at = DateTimeField(null=True)
    
    added_at = DateTimeField(default=datetime.datetime.now)

# --- 4. ACTIONS (The History Ledger) ---
class Action(BaseModel):
    account = ForeignKeyField(Account, backref='actions', field='device_id') 
    target = ForeignKeyField(Target, backref='interactions')
    action_type = CharField(default='follow') 
    result = CharField(default='success')
    timestamp = DateTimeField(default=datetime.datetime.now)


class SystemCommand(BaseModel):
    command = CharField()       # 'STOP_DEVICE', 'STOP_ALL', 'START_DEVICE'
    target_id = CharField(null=True) # device_id (e.g. 'margieserra96') or NULL for global
    status = CharField(default='pending') # pending, processing, completed, failed
    created_at = DateTimeField(default=datetime.datetime.now)
    executed_at = DateTimeField(null=True)


# --- 5. LOGS (Worker Feedback) ---
class DeviceLog(BaseModel):
    device_id = CharField()
    device_name = CharField()
    message = TextField()
    level = CharField(default='INFO') # INFO, ERROR, SUCCESS, WARNING
    timestamp = DateTimeField(default=datetime.datetime.now)
    is_sent = BooleanField(default=False) # Flag for frontend sync



# --- INITIALIZATION ---
def initialize_db():
    """Creates tables and ensures global keys exist."""
    db.connect(reuse_if_open=True)
    db.create_tables([SystemConfig, Account, Target, Action, SystemCommand, DeviceLog])
    
    # Initialize the Master Switch if it doesn't exist
    SystemConfig.get_or_create(key='global_automation_status', defaults={'value': 'OFF'})


def sync_devices_with_api(api_devices: List[Dict]):
    """ api_devices is the list from get_all_available_devices() """
    if api_devices is None:
        print("[DB] API Sync skipped due to API error (None received).")
        return

    api_ids = [d['id'] for d in api_devices]
    
    for device in api_devices:
        # We use the actual Geelark ID here
        acc, created = Account.get_or_create(
            device_id=device['id'], 
            defaults={
                'profile_name': device.get('name'), 
                'is_enabled': False,
                'status': 'active'
            }
        )
        if not created:
            # Sync name if changed
            if acc.profile_name != device.get('name'):
                acc.profile_name = device.get('name')
                acc.save()
            if acc.status != 'active':
                acc.status = 'active'
                acc.save()

    # Archive accounts that no longer exist in Geelark
    # SAFETY: Only archive if we got a valid list and it's not suspiciously empty 
    # (e.g., if we had 10 accounts and suddenly 0, but API said success, we still might want to be careful)
    if api_ids:
        (Account.update(status='archived', is_enabled=False)
         .where((Account.device_id.not_in(api_ids)) & (Account.status == 'active'))
         .execute())
    else:
        # If api_ids is empty, it means NO phones were returned.
        # We only archive if we are SURE this is intended.
        # For now, let's log a warning instead of mass-disabling everything.
        print("[DB] API returned 0 devices. Skipping archival to prevent accidental lockout.")

# --- SYSTEM CONTROLS ---

def pop_pending_command():
    """
    Fetches the oldest PENDING command and marks it as PROCESSING so no one else grabs it.
    Atomic transaction.
    """
    with db.atomic():
        cmd = (SystemCommand
               .select()
               .where(SystemCommand.status == 'pending')
               .order_by(SystemCommand.created_at.asc())
               .first())
        
        if cmd:
            cmd.status = 'processing'
            cmd.save()
            return cmd
    return None

def complete_command(cmd_id, status='completed'):
    SystemCommand.update(
        status=status, 
        executed_at=datetime.datetime.now()
    ).where(SystemCommand.id == cmd_id).execute()

def queue_command(command_type, target_id=None):
    """Helper for your API/CLI to insert commands easily."""
    SystemCommand.create(command=command_type, target_id=target_id)
    print(f"[DB] Queued command: {command_type} -> {target_id}")


def set_global_automation(state: bool):
    """Turns the whole farm ON or OFF."""
    val = 'ON' if state else 'OFF'
    SystemConfig.update(value=val).where(SystemConfig.key == 'global_automation_status').execute()

def is_automation_on() -> bool:
    try:
        conf = SystemConfig.get(SystemConfig.key == 'global_automation_status')
        return conf.value == 'ON'
    except: return False

# --- DYNAMIC CONFIG ---

DEFAULT_CONFIG = {
    "batch_size": 100,
    "session_limit_2h": 5,
    "min_batch_start": 1,
    "cooldown_hours": 2.0,
    "pattern_break": 4,
    "min_delay": 20,
    "max_delay": 45,
    "do_vetting": True,
    "continuous_mode": True
}

def get_session_config() -> Dict:
    """
    Fetches config from DB. If keys are missing, uses defaults.
    """
    import json
    try:
        conf_str = SystemConfig.get_or_none(SystemConfig.key == 'session_config')
        if conf_str:
            saved_conf = json.loads(conf_str.value)
            # Merge with defaults to ensure all keys exist
            return {**DEFAULT_CONFIG, **saved_conf}
    except Exception as e:
        print(f"[DB] Config load error: {e}")
    
    return DEFAULT_CONFIG

def update_session_config(new_config: Dict):
    """
    Updates the session config JSON in the DB.
    """
    import json
    # Ensure we are saving a valid JSON string
    # We merge with existing to allow partial updates
    current = get_session_config()
    updated = {**current, **new_config}
    
    val = json.dumps(updated)
    
    # Upsert
    SystemConfig.insert(key='session_config', value=val).on_conflict(
        conflict_target=[SystemConfig.key],
        preserve=[SystemConfig.value]
    ).execute()
    
    # Force update if insert didn't happen (peewee quirk with on_conflict)
    SystemConfig.update(value=val).where(SystemConfig.key == 'session_config').execute()

def set_account_enabled(device_id: str, enabled: bool):
    """Enables or disables a specific account for automation."""
    Account.update(is_enabled=enabled).where(Account.device_id == device_id).execute()

def disable_all_accounts():
    """Disables all active accounts."""
    Account.update(is_enabled=False).where(Account.status == 'active').execute()

def get_runnable_accounts() -> List[Account]:
    """Returns accounts that are both Active on Cloud and Enabled by User."""
    return list(Account.select().where(
        (Account.status == 'active') & 
        (Account.is_enabled == True)
    ))

# --- DATA INGESTION ---

def import_targets_from_file(filepath: str = 'targets.txt', source_tag: str = "manual_import") -> int:
    """Reads usernames from file and adds to DB. Cleans @ and duplicates."""
    if not os.path.exists(filepath): return 0
    
    with open(filepath, 'r') as f:
        lines = [l.strip().replace("@", "").lower() for l in f if l.strip()]
        unique_lines = list(set(lines))

    added = 0
    with db.atomic():
        for i in range(0, len(unique_lines), 100):
            chunk = unique_lines[i:i+100]
            data = [{"username": u, "source": source_tag} for u in chunk]
            # insert_many is very fast for large lists
            Target.insert_many(data).on_conflict_ignore().execute()
            added += len(chunk)
    return added

# --- HEAT MANAGEMENT & ALLOCATION ---

def get_account_heat_stats(account_id: str):
    """
    100,000 IQ Sliding Window Logic.
    Calculates activity in the last 2 hours and last 24 hours.
    """
    now = datetime.datetime.now()
    two_hours_ago = now - datetime.timedelta(hours=2)
    twenty_four_hours_ago = now - datetime.timedelta(hours=24)

    # 1. THE SPRINT: Actions in the last 2 hours
    recent_count = Action.select().where(
        (Action.account == account_id) & 
        (Action.action_type == 'follow') & 
        (Action.timestamp >= two_hours_ago)
    ).count()

    # 2. THE MARATHON: Actions in the last 24 hours (REPLACES Midnight check)
    daily_rolling_count = Action.select().where(
        (Action.account == account_id) & 
        (Action.action_type == 'follow') & 
        (Action.timestamp >= twenty_four_hours_ago)
    ).count()

    return {
        "recent_2h": recent_count,
        "rolling_24h": daily_rolling_count
    }
def get_total_pending_targets() -> int:
    return Target.select().where(Target.status == 'pending').count()

def reserve_targets(account_id: int, limit: int) -> List[str]:
    """
    The Atomic Lock: Reserves a batch of usernames so no other phone touches them.
    Returns list of strings (usernames).
    """
    reserved_usernames = []
    with db.atomic():
        # Select candidates
        candidates = (Target.select()
                      .where(Target.status == 'pending')
                      .limit(limit))
        
        if not candidates.exists(): return []
        
        reserved_usernames = [t.username for t in candidates]
        
        # Lock them
        (Target.update(
            status='reserved', 
            reserved_by=account_id, 
            reserved_at=datetime.datetime.now()
        ).where(Target.username.in_(reserved_usernames)).execute())
         
    return reserved_usernames

# --- WORKER LOGGING ---

def log_action(static_device_id: str, target_username: str, result: str):
    """
    Uses the PERSISTENT device_id (string) to identify the account.
    """
    try:
        # 1. Find the account by the string ID
        acc = Account.get(Account.device_id == static_device_id)
        
        # 2. Handle target finding
        tgt = Target.get(Target.username == target_username.lower())
        
        # 3. Update Target status
        final_status = 'completed' if result in ['success', 'already_following', 'requested'] else 'failed'
        tgt.status = final_status
        tgt.save()
        
        # 4. Create Action Log
        Action.create(
            account=acc, 
            target=tgt, 
            action_type='follow', 
            result=result
        )
    except Account.DoesNotExist:
        print(f"[DB ERROR] No account found with persistent ID: {static_device_id}")
    except Exception as e:
        print(f"[DB ERROR] Critical logging failure: {e}")

def release_targets(usernames: List[str],device_id=None):
    """Rolls back 'reserved' targets to 'pending' if a process crashes."""
    if not usernames: return
    (Target.update(status='pending', reserved_by=None, reserved_at=None)
     .where(Target.username.in_(usernames))
     .execute())

# --- THE JANITOR (Auto-Recovery) ---

def run_janitor_cleanup(timeout_minutes=30):
    """Resets targets stuck in 'reserved' status due to silent crashes."""
    cutoff = datetime.datetime.now() - datetime.timedelta(minutes=timeout_minutes)
    count = (Target.update(status='pending', reserved_by=None, reserved_at=None)
             .where((Target.status == 'reserved') & (Target.reserved_at < cutoff))
             .execute())
    if count:
        print(f"[Janitor] Cleaned up {count} stuck reservations.")

# --- UTILS ---

def get_db_stats():
    return {
        "pending": Target.select().where(Target.status == 'pending').count(),
        "completed": Target.select().where(Target.status == 'completed').count(),
        "failed": Target.select().where(Target.status == 'failed').count()
    }

def update_account_runtime_status(device_id, status):
    Account.update(runtime_status=status).where(Account.device_id == device_id).execute()

# --- HARD COOLDOWN MANAGEMENT ---

def set_account_cooldown(device_id: str, hours: float = 2.0):
    """
    Sets a hard cooldown for an account. Stored in DB, survives reboots.
    Returns the cooldown end time.
    """
    cooldown_end = datetime.datetime.now() + datetime.timedelta(hours=hours)
    Account.update(cooldown_until=cooldown_end).where(Account.device_id == device_id).execute()
    return cooldown_end

def clear_account_cooldown(device_id: str):
    """Clears cooldown (manual override or after natural expiry)."""
    Account.update(cooldown_until=None).where(Account.device_id == device_id).execute()

def get_account_cooldown_remaining(device_id: str) -> Optional[int]:
    """
    Returns minutes remaining in cooldown, or None if not in cooldown.
    """
    acc = Account.get_or_none(Account.device_id == device_id)
    if acc and acc.cooldown_until:
        remaining = (acc.cooldown_until - datetime.datetime.now()).total_seconds()
        if remaining > 0:
            return int(remaining / 60)  # Return minutes
    return None

# Initialization
if not os.path.exists(DB_NAME):
    initialize_db()

import_targets_from_file()
