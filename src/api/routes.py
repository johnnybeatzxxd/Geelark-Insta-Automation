from fastapi import APIRouter, HTTPException
from .schemas import AutomationStatus, DeviceSelection
from ..database import set_global_automation, is_automation_on, set_account_enabled, queue_command

router = APIRouter()

# --- AUTOMATION ENDPOINTS ---

@router.get("/automation/status", response_model=AutomationStatus)
def get_automation_status():
    """Get the current global automation state."""
    is_on = is_automation_on()
    return {
        "status": "ON" if is_on else "OFF",
        "message": "System is running" if is_on else "System is paused"
    }

@router.post("/automation/start", response_model=AutomationStatus)
def start_automation(selection: DeviceSelection):
    """
    Start automation.
    - If device_ids provided: Enables those specific accounts.
    - Always ensures Global Switch is ON.
    """
    # 1. Enable specific devices if requested
    if selection.device_ids:
        for dev_id in selection.device_ids:
            set_account_enabled(dev_id, True)
            
    # 2. Ensure global switch is ON so Manager picks them up
    set_global_automation(True)
    
    msg = f"Enabled {len(selection.device_ids)} devices" if selection.device_ids else "Global automation enabled"
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

from typing import List
from .schemas import AccountResponse, AccountStats
from ..database import Account, get_account_heat_stats

@router.get("/accounts", response_model=List[AccountResponse])
def list_accounts():
    """List all accounts known to the system."""
    accounts = list(Account.select())
    # Convert datetime to string for JSON serialization if needed, 
    # though Pydantic handles datetime objects well, we explicitly handle it if it's None
    return [
        AccountResponse(
            device_id=a.device_id,
            profile_name=a.profile_name,
            is_enabled=a.is_enabled,
            runtime_status=a.runtime_status,
            status=a.status,
            daily_limit=a.daily_limit,
            cooldown_until=str(a.cooldown_until) if a.cooldown_until else None
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
