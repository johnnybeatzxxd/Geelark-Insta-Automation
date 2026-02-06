from fastapi import APIRouter, HTTPException
from .schemas import AutomationStatus, DeviceSelection, AccountResponse
from database import set_global_automation, is_automation_on, set_account_enabled, queue_command, clear_account_cooldown, configure_and_enable_accounts, sync_devices_with_api
from urllib.parse import urlparse
from geelark_api import get_available_phones

router = APIRouter()

ws_router = APIRouter() 
# --- AUTOMATION ENDPOINTS ---

@router.get("/automation/status", response_model=AutomationStatus)
def get_automation_status():
    """
    Get the current global automation state.
    Returns detailed stats for every account (READ ONLY - FAST).
    """
    is_on = is_automation_on()
    
    # Fetch all accounts - NO CALCULATIONS needed here anymore
    accounts = list(
        Account.select()
        .where(Account.status == 'active')
        .order_by(Account.device_id.desc())
    )
    account_details = []
    
    for a in accounts:
        account_details.append({
            "device_id": a.device_id,
            "profile_name": a.profile_name,
            "is_enabled": a.is_enabled,
            "runtime_status": a.runtime_status,
            "status": a.status,
            "daily_limit": a.daily_limit,
            "cooldown_until": str(a.cooldown_until) if a.cooldown_until else None,
            "stream_url": a.stream_url,
            "task_mode": a.task_mode,
            "warmup_day": a.warmup_day,
            "group_name": a.group_name,
            "stats": {
                "recent_2h": a.cached_2h_count,
                "rolling_24h": a.cached_24h_count
            }
        })

    return {
        "status": "ON" if is_on else "OFF",
        "message": "System is running" if is_on else "System is paused",
        "accounts": account_details
    }

@router.post("/automation/start", response_model=AutomationStatus)
def start_automation(selection: DeviceSelection):
    """
    Start automation.
    - If device_ids provided: Enables those specific accounts.
    - Always ensures Global Switch is ON.
    """
    update_data = {
        'task_mode': selection.mode, 
        'is_enabled': True
    }

    configure_and_enable_accounts(
        device_ids=selection.device_ids, 
        mode=selection.mode, 
        warmup_day=selection.warmup_day if selection.mode == 'warmup' else None
    )
            
    # 2. Ensure global switch is ON so Manager picks them up
    set_global_automation(True)
    
    msg = f"Started {len(selection.device_ids) if selection.device_ids else 'all'} devices in {selection.mode} mode."
    if selection.mode == 'warmup':
        msg += f" (Day {selection.warmup_day})"
        
    return {
        "status": "ON",
        "message": msg
    }

@router.post("/automation/stop", response_model=AutomationStatus)
def stop_automation(selection: DeviceSelection):
    """
    Stop automation.
    - If device_ids provided: Queues STOP_DEVICE for them and disables them.
    - If NO device_ids: Queues STOP_ALL and turns off Global Switch.
    """
    if selection.device_ids:
        # Stop specific devices
        for dev_id in selection.device_ids:
            set_account_enabled(dev_id, False) # Prevent restart
            queue_command("STOP_DEVICE", target_id=dev_id) # Kill current process
        
        return {
            "status": "ON" if is_automation_on() else "OFF",
            "message": f"Stopping {len(selection.device_ids)} devices..."
        }
    else:
        # Stop EVERYTHING
        set_global_automation(False)
        queue_command("STOP_ALL")
        return {
            "status": "OFF",
            "message": "Global automation disabled. Stopping all workers."
        }

# --- ACCOUNT ENDPOINTS ---

from typing import List, Optional
from .schemas import AccountResponse, AccountStats
from database import Account, get_account_heat_stats

@router.get("/accounts", response_model=List[AccountResponse])
def list_accounts():
    """List all accounts known to the system."""
    accounts = list(Account.select().where(Account.status == 'active'))
    # though Pydantic handles datetime objects well, we explicitly handle it if it's None
    return [
        AccountResponse(
            device_id=a.device_id,
            profile_name=a.profile_name,
            is_enabled=a.is_enabled,
            runtime_status=a.runtime_status,
            status=a.status,
            daily_limit=a.daily_limit,
            cooldown_until=str(a.cooldown_until) if a.cooldown_until else None,
            stream_url=a.stream_url
        ) for a in accounts
    ]

@router.patch("/accounts/{device_id}/enable", response_model=AccountResponse)
def enable_account(device_id: str):
    """Enable a specific account."""
    set_account_enabled(device_id, True)
    # Fetch updated
    a = Account.get(Account.device_id == device_id)
    return AccountResponse(
        device_id=a.device_id,
        profile_name=a.profile_name,
        is_enabled=a.is_enabled,
        runtime_status=a.runtime_status,
        status=a.status,
        daily_limit=a.daily_limit,
        cooldown_until=str(a.cooldown_until) if a.cooldown_until else None
    )

@router.patch("/accounts/{device_id}/disable", response_model=AccountResponse)
def disable_account(device_id: str):
    """Disable a specific account and stop it if running."""
    set_account_enabled(device_id, False)
    queue_command("STOP_DEVICE", target_id=device_id)
    
    a = Account.get(Account.device_id == device_id)
    return AccountResponse(
        device_id=a.device_id,
        profile_name=a.profile_name,
        is_enabled=a.is_enabled,
        runtime_status=a.runtime_status,
        status=a.status,
        daily_limit=a.daily_limit,
        cooldown_until=str(a.cooldown_until) if a.cooldown_until else None
    )

@router.get("/accounts/{device_id}/stats", response_model=AccountStats)
def get_account_stats(device_id: str):
    """Get heat stats (activity counts) for an account."""
    stats = get_account_heat_stats(device_id)
    return stats

# --- TARGET ENDPOINTS ---

from .schemas import TargetResponse, TargetBase, TargetStats
from database import Target, get_db_stats

@router.get("/targets", response_model=List[TargetResponse])
def list_targets(page: int = 1, limit: int = 50, status: Optional[str] = None):
    """List targets with optional status filter and pagination."""
    query = Target.select()
    if status:
        query = query.where(Target.status == status)
    
    # Pagination
    targets = query.order_by(Target.added_at.desc()).paginate(page, limit)
    
    return [
        TargetResponse(
            username=t.username,
            source=t.source,
            status=t.status,
            reserved_by=t.reserved_by.device_id if t.reserved_by else None,
            added_at=str(t.added_at)
        ) for t in targets
    ]

@router.post("/targets", response_model=dict)
def add_targets(targets: List[TargetBase]):
    """Bulk add targets."""
    
    def extract_username(input_str: str) -> str:
        input_str = input_str.strip().lstrip('@')
        if input_str.startswith('http://') or input_str.startswith('https://'):
            parsed = urlparse(input_str)
            if parsed.hostname and 'instagram.com' in parsed.hostname:
                path = parsed.path.strip('/')
                if path:
                    return path.split('/')[0].lower()
        return input_str.lower()
    
    # Prepare data for bulk insert
    data = [{"username": extract_username(t.username), "source": t.source} for t in targets]
    
    # Use insert_many with on_conflict_ignore to skip duplicates
    with Target._meta.database.atomic():
        for i in range(0, len(data), 100):
            chunk = data[i:i+100]
            Target.insert_many(chunk).on_conflict_ignore().execute()
            
    return {"message": f"Processed {len(targets)} targets (duplicates ignored)."}

@router.get("/targets/stats", response_model=TargetStats)
def get_target_stats():
    """Get counts of targets by status."""
    stats = get_db_stats()
    return stats

# --- LOG ENDPOINTS ---

from fastapi import WebSocket, WebSocketDisconnect
from .schemas import LogResponse
from database import DeviceLog
import asyncio

@router.get("/logs", response_model=List[LogResponse])
def get_logs(limit: int = 100, device_id: Optional[str] = None):
    """Get latest logs, optionally filtered by device."""
    query = DeviceLog.select().order_by(DeviceLog.timestamp.desc()).limit(limit)
    if device_id:
        query = query.where(DeviceLog.device_id == device_id)
        
    return [
        LogResponse(
            id=l.id,
            device_id=l.device_id,
            device_name=l.device_name,
            message=l.message,
            level=l.level,
            timestamp=str(l.timestamp)
        ) for l in query
    ]

@ws_router.websocket("/logs/ws/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: str):
    """
    Real-time log streamer. 
    Currently implements a 'tail -f' style poll from DB for simplicity.
    """
    await websocket.accept()
    last_id = 0
    
    # Send initial batch of recent logs
    recent = (DeviceLog.select()
              .where(DeviceLog.device_id == device_id)
              .order_by(DeviceLog.timestamp.desc())
              .limit(10))
    
    # We want them in chronological order for the stream
    for l in reversed(list(recent)):
        await websocket.send_json({
            "timestamp": str(l.timestamp),
            "level": l.level,
            "message": l.message
        })
        last_id = max(last_id, l.id)
        
    try:
        while True:
            # Poll for new logs every second
            await asyncio.sleep(1)
            new_logs = (DeviceLog.select()
                        .where((DeviceLog.device_id == device_id) & (DeviceLog.id > last_id))
                        .order_by(DeviceLog.timestamp.asc()))
            
            for l in new_logs:
                await websocket.send_json({
                    "timestamp": str(l.timestamp),
                    "level": l.level,
                    "message": l.message
                })
                last_id = l.id
                
    except WebSocketDisconnect:
        print(f"Client disconnected from log stream for {device_id}")

# --- CONFIG ENDPOINTS ---

from .schemas import SessionConfig
from database import get_session_config, update_session_config

@router.get("/config", response_model=SessionConfig)
def get_config():
    """Get current session configuration."""
    return get_session_config()

@router.patch("/config", response_model=SessionConfig)
def update_config(config: SessionConfig):
    """
    Update session configuration.
    The Manager will pick up these changes on its next cycle (within seconds).
    """
    # Convert Pydantic model to dict, excluding defaults if you wanted partial updates,
    # but here we want to save the whole state.
    update_session_config(config.dict())
    return get_session_config()

@router.patch("/accounts/{device_id}/clear_cooldown", response_model=AccountResponse)
def clear_cooldown(device_id: str):
    """Clear cooldown for a specific account."""
    clear_account_cooldown(device_id)
    
    try:
        a = Account.get(Account.device_id == device_id)
        return AccountResponse(
            device_id=a.device_id,
            profile_name=a.profile_name,
            is_enabled=a.is_enabled,
            runtime_status=a.runtime_status,
            status=a.status,
            daily_limit=a.daily_limit,
            cooldown_until=str(a.cooldown_until) if a.cooldown_until else None,
            stream_url=a.stream_url
        )
    except Account.DoesNotExist:
        raise HTTPException(status_code=404, detail="Account not found")

@router.post("/system/sync_devices")
def trigger_device_sync():
    """
    1. Fetches from Cloud.
    2. Updates DB immediately (for Frontend).
    3. Tells Manager to update its RAM (for Workers).
    """
    try:
        # 1. Fetch & Update DB (So user sees results instantly)
        devices = get_available_phones()
        if devices is None:
            raise HTTPException(status_code=502, detail="Geelark API failed")
            
        sync_devices_with_api(devices)
        
        # 2. Signal the Manager (So automation picks up new phones instantly)
        queue_command("FORCE_SYNC")
        
        return {
            "status": "success", 
            "message": f"Synced {len(devices)} devices. Manager signaled."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
