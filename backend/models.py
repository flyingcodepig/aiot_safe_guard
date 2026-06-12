"""Pydantic 数据模型"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class CommandRequest(BaseModel):
    user_id: str
    user_input: str
    device_id: str
    action: str
    params: Optional[Dict[str, Any]] = Field(default_factory=dict)

class CommandResponse(BaseModel):
    request_id: str
    user_id: str
    user_role: str
    device_id: str
    action: str
    final_decision: str  # "allow" | "block" | "require_confirm"
    policy_check: Dict[str, Any]
    physical_check: Dict[str, Any]
    device_state_after: Optional[Dict[str, Any]]
    block_reasons: List[str]
    message: str
    risk_result: Optional[Dict[str, Any]] = None

class AuditLogEntry(BaseModel):
    id: Optional[int]
    request_id: str
    user_input: str
    user_role: str
    target_device: str
    target_action: str
    input_guard_result: Optional[str]
    fact_check_result: Optional[str]
    policy_result: Optional[str]
    physical_result: Optional[str]
    risk_result: Optional[str] = None
    final_decision: str
    block_reasons: Optional[str]
    timestamp: Optional[datetime]
