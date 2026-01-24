from pydantic import BaseModel
from typing import List, Optional

class AutomationStatus(BaseModel):
    status: str  # "ON" or "OFF"
    message: str

class DeviceSelection(BaseModel):
    device_ids: Optional[List[str]] = None

class AccountResponse(BaseModel):
    device_id: str
    profile_name: Optional[str]
    is_enabled: bool
    runtime_status: str
    status: str
    daily_limit: int
    cooldown_until: Optional[str] = None # Serialized datetime

class AccountStats(BaseModel):
    recent_2h: int
    rolling_24h: int
