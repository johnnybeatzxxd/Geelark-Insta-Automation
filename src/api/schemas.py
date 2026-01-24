from pydantic import BaseModel
from typing import List, Optional

class AccountStats(BaseModel):
    recent_2h: int
    rolling_24h: int

class AccountDetail(BaseModel):
    device_id: str
    profile_name: Optional[str]
    is_enabled: bool
    runtime_status: str
    status: str
    daily_limit: int
    cooldown_until: Optional[str] = None
    stream_url: Optional[str] = None
    stats: AccountStats

class TargetBase(BaseModel):
    username: str
    source: Optional[str] = "api"

class TargetResponse(TargetBase):
    status: str
    reserved_by: Optional[str] = None
    added_at: str # Serialized datetime

class TargetStats(BaseModel):
    pending: int
    completed: int
    failed: int

class LogResponse(BaseModel):
    id: int
    device_id: str
    device_name: str
    message: str
    level: str
    timestamp: str

class SessionConfig(BaseModel):
    batch_size: int = 100
    session_limit_2h: int = 5
    min_batch_start: int = 1
    cooldown_hours: float = 2.0
    pattern_break: int = 4
    min_delay: int = 20
    max_delay: int = 45
    do_vetting: bool = True

class AutomationStatus(BaseModel):
    status: str  # "ON" or "OFF"
    message: str
    accounts: List[AccountDetail] = []

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
    stream_url: Optional[str] = None

class AccountStats(BaseModel):
    recent_2h: int
    rolling_24h: int
