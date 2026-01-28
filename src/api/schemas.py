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

# 1. Helper Models for the Warmup JSON structure
class WarmupFeature(BaseModel):
    enabled: bool
    minScrolls: Optional[int] = None
    maxScrolls: Optional[int] = None
    minMinutes: Optional[int] = None
    maxMinutes: Optional[int] = None

class WarmupLimits(BaseModel):
    maxLikes: int
    maxFollows: int

class WarmupChance(BaseModel):
    follow: int
    like: int
    comment: int

class DayConfig(BaseModel):
    label: str
    feed: WarmupFeature
    reels: WarmupFeature
    limits: WarmupLimits
    speed: str
    chance: WarmupChance

# 2. Update the Main SessionConfig
class SessionConfig(BaseModel):
    batch_size: int
    session_limit_2h: int
    min_batch_start: int
    cooldown_hours: Optional[float] = 2.0
    pattern_break: int
    min_delay: int
    max_delay: int
    do_vetting: bool
    continuous_mode: bool = True
    max_concurrent_sessions: int = 5
    
    warmup_strategy: dict[str, DayConfig] 

class AutomationStatus(BaseModel):
    status: str  # "ON" or "OFF"
    message: str
    accounts: List[AccountDetail] = []

class DeviceSelection(BaseModel):
    device_ids: Optional[List[str]] = None
    mode: str = "follow"
    warmup_day: Optional[int] = 1

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
