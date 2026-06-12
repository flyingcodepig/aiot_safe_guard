"""
智御物联 - AIoT安全中间件
FastAPI 主入口 (阶段4: 集成输入安全检测 + 事实校验)
"""
from contextlib import asynccontextmanager
import csv
import io
import uuid
import os
import json as json_module
import time
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Body, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from database import init_db, get_connection, reset_db
from device_loader import DeviceCapabilityLoader
from sandbox import SandboxEngine
from policy_engine import PolicyEngine
from physical_checker import PhysicalChecker
from audit import AuditLogger
from models import CommandRequest, CommandResponse
from llm_planner import LLMPlanner, ActionParser, FallbackMatcher
from input_guard import InputGuard
from fact_checker import FactChecker
from selfcheck_integration import SelfCheckWrapper
from risk_scoring import score_action, score_overall


# ---------- 数据模型 ----------
class SmartCommandRequest(BaseModel):
    user_id: str
    user_input: str

class SmartCommandResponse(BaseModel):
    request_id: str
    user_id: str
    user_role: str
    user_input: str
    llm_actions: List[Dict[str, Any]]
    parsed_actions: List[Dict[str, Any]]
    action_results: List[Dict[str, Any]]
    overall_decision: str
    input_guard_result: Optional[Dict[str, Any]] = None
    risk_result: Optional[Dict[str, Any]] = None
    timings_ms: Optional[Dict[str, float]] = None
    require_confirmation: bool = False
    confirmation_token: Optional[str] = None

class PolicyCreateRequest(BaseModel):
    role: str
    device_type: str
    action_pattern: str
    decision: str
    priority: int = 0
    conditions: Optional[str] = None
    description: Optional[str] = ""
    enabled: int = 1

class PhysicalRuleCreateRequest(BaseModel):
    device_type: str
    rule_type: str
    config: str
    description: Optional[str] = ""
    enabled: int = 1


# ---------- 生命周期 ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    global device_loader, sandbox, policy_engine, physical_checker, audit_logger
    global llm_planner, action_parser, fallback_matcher, input_guard, fact_checker, selfcheck_wrapper

    import config

    device_loader = DeviceCapabilityLoader(config.DEVICE_CONFIG_DIR)
    sandbox = SandboxEngine(device_loader)
    policy_engine = PolicyEngine()
    physical_checker = PhysicalChecker(device_loader, sandbox)
    audit_logger = AuditLogger()

    model_name = os.getenv("LLM_MODEL", "deepseek-chat")
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
    llm_planner = LLMPlanner(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        timeout=app_config.LLM_TIMEOUT_SECONDS,
        max_retries=app_config.LLM_MAX_RETRIES,
        enabled=app_config.ENABLE_LLM_PLANNER,
    )
    llm_planner.build_system_prompt(device_loader)
    action_parser = ActionParser(device_loader)
    fallback_matcher = FallbackMatcher(device_loader)

    input_guard = InputGuard(
        llm_client=llm_planner.client,
        llm_model=model_name,
        enable_llm_guard=config.ENABLE_LLM_GUARD_SCANNER,
    )
    fact_checker = FactChecker(
        device_loader,
        llm_client=llm_planner.client,
        llm_model=model_name,
        enable_llm_checks=app_config.ENABLE_LLM_FACT_CHECKS,
    )

    if config.SELFCHECK_ENABLED:
        selfcheck_wrapper = SelfCheckWrapper(
            method=config.SELFCHECK_METHOD,
            client=llm_planner.client,
            model=model_name,
            threshold=config.SELFCHECK_THRESHOLD,
        )
        print(f"SelfCheckGPT 已启用: method={config.SELFCHECK_METHOD}")
    else:
        selfcheck_wrapper = None

    print(f"LLM 规划器已初始化: model={model_name}, base_url={base_url}")
    print("智御物联系统启动完成（阶段5：集成SelfCheckGPT幻觉检测）")
    yield
    print("系统关闭")


app = FastAPI(title="智御物联 - AIoT安全中间件", version="4.0.0", lifespan=lifespan)

# 配置 CORS
import config as app_config
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

SAFETY_LAYER_NAMES = {
    "input_guard",
    "device_gate",
    "intent_gate",
    "fact_checker",
    "policy_engine",
    "physical_checker",
    "selfcheck",
}

SAFETY_LAYER_DEFAULTS = {
    "input_guard": app_config.ENABLE_INPUT_GUARD,
    "device_gate": app_config.ENABLE_DEVICE_GATE,
    "intent_gate": app_config.ENABLE_INTENT_GATE,
    "fact_checker": app_config.ENABLE_FACT_CHECKER,
    "policy_engine": app_config.ENABLE_POLICY_ENGINE,
    "physical_checker": app_config.ENABLE_PHYSICAL_CHECKER,
    "selfcheck": app_config.ENABLE_SELFCHECK_GATE,
}


def get_safety_layers(request: Optional[Request] = None) -> Dict[str, bool]:
    layers = dict(SAFETY_LAYER_DEFAULTS)
    if request is None:
        return layers

    disabled = request.headers.get("X-Ablation-Disable", "")
    for name in [part.strip() for part in disabled.split(",") if part.strip()]:
        if name in SAFETY_LAYER_NAMES:
            layers[name] = False
    return layers


def disabled_layers(layers: Dict[str, bool]) -> List[str]:
    return [name for name, enabled in sorted(layers.items()) if not enabled]


def mentioned_device_ids(user_input: str) -> List[str]:
    return [
        device_id
        for device_id in device_loader.devices
        if device_loader.device_mentioned_in_input(device_id, user_input)
    ]


def no_action_risk(
    user_role: str,
    input_guard_result: Dict[str, Any],
    reason: str,
    policy_decision: str = "block",
) -> Dict[str, Any]:
    action_score = score_action(
        user_role=user_role,
        input_guard_result=input_guard_result,
        device_loader=device_loader,
        policy_result={"decision": policy_decision, "reason": reason},
        physical_result={"decision": "pass", "reason": "not executed"},
        fact_result={"is_valid": policy_decision != "block", "reasons": [reason]},
        raw_actions=[],
        parsed_actions=[],
    )
    return score_overall([], action_score)


def direct_command_risk(
    user_role: str,
    input_guard_result: Dict[str, Any],
    device_id: str,
    device_type: str,
    action: str,
    params: Dict[str, Any],
    policy_result: Dict[str, Any],
    physical_result: Dict[str, Any],
    fact_result: Dict[str, Any],
) -> Dict[str, Any]:
    return score_action(
        user_role=user_role,
        input_guard_result=input_guard_result,
        device_loader=device_loader,
        device_id=device_id,
        device_type=device_type,
        action=action,
        params=params,
        policy_result=policy_result,
        physical_result=physical_result,
        fact_result=fact_result,
    )


def elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)


def add_timing(timings: Dict[str, float], name: str, start: float) -> None:
    timings[name] = round(timings.get(name, 0.0) + elapsed_ms(start), 2)


def finalize_timings(timings: Dict[str, float], request_start: float) -> Dict[str, float]:
    timings["total"] = elapsed_ms(request_start)
    return timings


# API Key 认证中间件（纯 ASGI 中间件，与 FastAPI 完全兼容）
from starlette.responses import JSONResponse

SKIP_AUTH_PREFIXES = ("/static", "/health")
SKIP_AUTH_EXACT = {"/", "/api/config"}

class APIKeyMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope["path"]
        if path in SKIP_AUTH_EXACT or path.startswith(SKIP_AUTH_PREFIXES):
            await self.app(scope, receive, send)
            return

        if not app_config.API_KEY:
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        api_key = headers.get(b"x-api-key", b"").decode()
        if api_key != app_config.API_KEY:
            response = JSONResponse(
                {"detail": "无效的 API Key", "hint": "请在请求头中设置 X-API-Key"},
                status_code=401,
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)

app.add_middleware(APIKeyMiddleware)

_static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/static", StaticFiles(directory=_static_dir), name="static")


# ---------- 基础端点 ----------
@app.get("/")
async def root():
    return {"message": "智御物联 AIoT安全中间件", "version": "4.0.0"}

@app.get("/api/config")
async def get_config():
    return {
        "llm_model": os.getenv("LLM_MODEL", "deepseek-chat"),
        "llm_base_url": os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),
        "openai_key_set": bool(os.getenv("OPENAI_API_KEY")),
        "llm_planner_enabled": app_config.ENABLE_LLM_PLANNER,
        "llm_fact_checks_enabled": app_config.ENABLE_LLM_FACT_CHECKS,
        "safety_layers": SAFETY_LAYER_DEFAULTS,
    }

@app.get("/api/ablation/config")
async def get_ablation_config():
    return {
        "layers": sorted(SAFETY_LAYER_NAMES),
        "defaults": SAFETY_LAYER_DEFAULTS,
        "request_header": "X-Ablation-Disable",
        "example": "X-Ablation-Disable: input_guard,fact_checker",
    }

@app.get("/health")
async def health_check():
    try:
        conn = get_connection()
        conn.execute("SELECT 1")
        conn.close()
        db_status = "ok"
    except Exception as exc:
        db_status = f"error: {exc}"

    loaded_devices = len(getattr(device_loader, "devices", {})) if "device_loader" in globals() else 0
    status = "ok" if db_status == "ok" and loaded_devices > 0 else "degraded"
    return {
        "status": status,
        "database": db_status,
        "loaded_devices": loaded_devices,
        "version": "4.0.0",
    }


# ---------- 直接命令 ----------
@app.post("/api/command", response_model=CommandResponse)
async def process_command(req: CommandRequest, request: Request):
    request_id = f"REQ_{uuid.uuid4().hex[:8]}"
    block_reasons = []
    user_role = policy_engine.get_user_role(req.user_id)

    # 输入安全检测
    guard_result = input_guard.scan(req.user_input, user_role)
    if guard_result["risk_level"] == "high":
        block_reasons.append("输入安全检测: 高风险")
        risk_result = direct_command_risk(
            user_role, guard_result, req.device_id, device_loader.get_device_type(req.device_id),
            req.action, req.params or {}, {"decision": "block", "reason": "input guard high risk"},
            {"decision": "pass", "reason": "not executed"},
            {"is_valid": False, "reasons": ["input guard high risk"]},
        )
        audit_logger.log(request_id, req.user_input, user_role, req.device_id, req.action,
                         guard_result, {}, {}, {}, "block", block_reasons, risk_result)
        return CommandResponse(
            request_id=request_id, user_id=req.user_id, user_role=user_role,
            device_id=req.device_id, action=req.action, final_decision="block",
            policy_check={"decision": "fail", "reason": "输入安全检测拦截"},
            physical_check={"decision": "pass", "reason": "未执行"},
            device_state_after=None, block_reasons=block_reasons,
            message="输入被安全检测拦截",
            risk_result=risk_result,
        )
    if guard_result["risk_level"] == "medium":
        # 受信客户端（有API Key或开发模式）放行并记录，否则拦截
        api_key = request.headers.get("X-API-Key", "")
        is_trusted = not app_config.API_KEY or api_key == app_config.API_KEY
        if is_trusted:
            block_reasons.append("输入安全检测: 中风险（受信客户端放行）")
        else:
            block_reasons.append("输入安全检测: 中风险，直接命令端点需人工审核")
            risk_result = direct_command_risk(
                user_role, guard_result, req.device_id, device_loader.get_device_type(req.device_id),
                req.action, req.params or {}, {"decision": "block", "reason": "input guard medium risk"},
                {"decision": "pass", "reason": "not executed"},
                {"is_valid": False, "reasons": ["input guard medium risk"]},
            )
            audit_logger.log(request_id, req.user_input, user_role, req.device_id, req.action,
                             guard_result, {}, {}, {}, "block", block_reasons, risk_result)
            return CommandResponse(
                request_id=request_id, user_id=req.user_id, user_role=user_role,
                device_id=req.device_id, action=req.action, final_decision="block",
                policy_check={"decision": "fail", "reason": "输入安全检测: 中风险"},
                physical_check={"decision": "pass", "reason": "未执行"},
                device_state_after=None, block_reasons=block_reasons,
                message="输入触发安全检测，请添加 X-API-Key 请求头或使用 /api/smart_command 端点",
                risk_result=risk_result,
            )

    device_type = device_loader.get_device_type(req.device_id)

    if not device_type or device_type == "unknown":
        block_reasons = [f"设备 {req.device_id} 不存在"]
        risk_result = direct_command_risk(
            user_role, guard_result, req.device_id, "unknown", req.action, req.params or {},
            {"decision": "block", "reason": "unknown device"},
            {"decision": "pass", "reason": "not executed"},
            {"is_valid": False, "reasons": ["unknown device"]},
        )
        audit_logger.log(request_id, req.user_input, user_role, req.device_id, req.action,
                         guard_result, {"is_valid": False, "reasons": ["unknown device"]},
                         {"decision": "block", "reason": "unknown device"}, {},
                         "block", block_reasons, risk_result)
        return CommandResponse(
            request_id=request_id, user_id=req.user_id, user_role=user_role,
            device_id=req.device_id, action=req.action, final_decision="block",
            policy_check={"decision": "fail", "reason": f"设备 {req.device_id} 不存在"},
            physical_check={"decision": "pass", "reason": ""},
            device_state_after=None, block_reasons=block_reasons,
            message=f"设备 {req.device_id} 不存在",
            risk_result=risk_result,
        )

    # 事实校验 — 参数 Schema 检查
    is_valid, fact_risk, fact_reasons = fact_checker.check(
        req.device_id, req.action, req.params or {}, user_role
    )
    if not is_valid:
        block_reasons.append(f"事实校验失败: {'; '.join(fact_reasons)}")
        fact_result = {"is_valid": False, "reasons": fact_reasons}
        risk_result = direct_command_risk(
            user_role, guard_result, req.device_id, device_type, req.action, req.params or {},
            {"decision": "block", "reason": "fact check failed"},
            {"decision": "pass", "reason": "not executed"},
            fact_result,
        )
        audit_logger.log(request_id, req.user_input, user_role, req.device_id, req.action,
                         guard_result, fact_result, {}, {}, "block", block_reasons, risk_result)
        return CommandResponse(
            request_id=request_id, user_id=req.user_id, user_role=user_role,
            device_id=req.device_id, action=req.action, final_decision="block",
            policy_check={"decision": "fail", "reason": f"事实校验: {'; '.join(fact_reasons)}"},
            physical_check={"decision": "pass", "reason": "未执行"},
            device_state_after=None, block_reasons=block_reasons,
            message=f"参数校验失败: {'; '.join(fact_reasons)}",
            risk_result=risk_result,
        )

    pd, pr, pr2 = policy_engine.check(user_role, device_type, req.action)
    policy_result = {"decision": pd, "matched_rule": pr, "reason": pr2}
    if pd == "block":
        block_reasons.append(f"权限拒绝: {pr2}")
        risk_result = direct_command_risk(
            user_role, guard_result, req.device_id, device_type, req.action, req.params or {},
            policy_result,
            {"decision": "pass", "reason": "not executed"},
            {"is_valid": True},
        )
        audit_logger.log(request_id, req.user_input, user_role, req.device_id, req.action,
                         guard_result, {"is_valid": True}, policy_result, {},
                         "block", block_reasons, risk_result)
        return CommandResponse(
            request_id=request_id, user_id=req.user_id, user_role=user_role,
            device_id=req.device_id, action=req.action, final_decision="block",
            policy_check=policy_result, physical_check={"decision": "pass", "reason": "未执行"},
            device_state_after=None, block_reasons=block_reasons, message=f"操作被拒绝: {pr2}",
            risk_result=risk_result,
        )

    phys_decision, phys_reason, safe_alt = physical_checker.check(req.device_id, req.action, req.params or {})
    physical_result = {"decision": phys_decision, "reason": phys_reason, "safe_alternative": safe_alt}
    if phys_decision == "fail":
        block_reasons.append(f"物理边界: {phys_reason}")
        alt_msg = f"，建议值为 {safe_alt}" if safe_alt else ""
        risk_result = direct_command_risk(
            user_role, guard_result, req.device_id, device_type, req.action, req.params or {},
            policy_result, physical_result, {"is_valid": True},
        )
        audit_logger.log(request_id, req.user_input, user_role, req.device_id, req.action,
                         guard_result, {"is_valid": True}, policy_result, physical_result,
                         "block", block_reasons, risk_result)
        return CommandResponse(
            request_id=request_id, user_id=req.user_id, user_role=user_role,
            device_id=req.device_id, action=req.action, final_decision="block",
            policy_check=policy_result, physical_check=physical_result, device_state_after=None,
            block_reasons=block_reasons, message=f"操作被拒绝: {phys_reason}{alt_msg}",
            risk_result=risk_result,
        )

    success, msg, new_state, transport_result = sandbox.execute(req.device_id, req.action, req.params or {})
    if not success:
        block_reasons.append(f"执行失败: {msg}")
    final_decision = "allow" if success else "block"
    risk_result = direct_command_risk(
        user_role, guard_result, req.device_id, device_type, req.action, req.params or {},
        policy_result, physical_result, {"is_valid": True},
    )
    audit_logger.log(request_id, req.user_input, user_role, req.device_id, req.action,
                     guard_result, {"is_valid": True}, policy_result, physical_result,
                     final_decision, block_reasons, risk_result, transport_result if success else None)
    return CommandResponse(
        request_id=request_id, user_id=req.user_id, user_role=user_role,
        device_id=req.device_id, action=req.action, final_decision=final_decision,
        policy_check=policy_result, physical_check=physical_result,
        device_state_after=new_state if success else None,
        block_reasons=block_reasons, message=msg,
        risk_result=risk_result,
        transport_result=transport_result if success else None,
    )


# ---------- 设备状态 ----------
@app.get("/api/device/{device_id}/state")
async def get_device_state(device_id: str):
    if not device_loader.device_exists(device_id):
        raise HTTPException(status_code=404, detail=f"设备 {device_id} 不存在")
    state = sandbox.get_device_state(device_id)
    device = device_loader.get_device(device_id)
    return {"device_id": device_id, "name": device.name, "type": device.type, "state": state}

@app.post("/api/device/{device_id}/set_state")
async def set_device_state(device_id: str, key: str = Body(...), value: str = Body(...)):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO device_states (device_id, key, value) VALUES (?,?,?)",
              (device_id, key, value))
    conn.commit()
    conn.close()
    return {"message": f"{device_id}.{key} = {value}"}

@app.get("/api/devices")
async def list_devices():
    devices = []
    for device_id, device in device_loader.devices.items():
        state = sandbox.get_device_state(device_id)
        devices.append({"device_id": device_id, "name": device.name, "type": device.type, "state": state})
    return {"devices": devices}

@app.get("/api/stats")
async def get_stats():
    return audit_logger.get_stats()

@app.get("/api/logs")
async def get_logs(limit: int = 50, final_decision: Optional[str] = None, user_role: Optional[str] = None):
    safe_limit = max(1, min(limit, 10000))
    return audit_logger.get_recent_logs(safe_limit, final_decision=final_decision, user_role=user_role)

@app.get("/api/logs/export")
async def export_logs(
    format: str = "json",
    limit: int = 10000,
    final_decision: Optional[str] = None,
    user_role: Optional[str] = None,
):
    safe_limit = max(1, min(limit, 10000))
    logs = audit_logger.get_recent_logs(safe_limit, final_decision=final_decision, user_role=user_role)
    export_format = format.lower()

    if export_format == "json":
        body = json_module.dumps(logs, ensure_ascii=False, indent=2)
        return Response(
            content=body,
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=audit_logs.json"},
        )

    if export_format == "csv":
        output = io.StringIO()
        fieldnames = [
            "timestamp", "request_id", "user_role", "target_device", "target_action",
            "final_decision", "risk_result", "transport_result", "block_reasons", "user_input",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(logs)
        return Response(
            content=output.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
        )

    raise HTTPException(status_code=400, detail="format must be csv or json")


# ---------- LLM 规划 ----------
@app.post("/api/llm/plan")
async def llm_plan(user_input: str):
    raw_actions = llm_planner.plan(user_input)
    parsed_actions = action_parser.parse(raw_actions)
    return {"user_input": user_input, "raw_llm_output": raw_actions, "parsed_actions": parsed_actions}


# ---------- 管道执行器（可复用） ----------
async def execute_smart_pipeline(user_id: str, user_input: str,
                                  request_id: str, user_role: str,
                                  input_guard_result: dict,
                                  safety_layers: Optional[Dict[str, bool]] = None,
                                  timings: Optional[Dict[str, float]] = None,
                                  request_start: Optional[float] = None) -> SmartCommandResponse:
    timings = timings or {}
    request_start = request_start or time.perf_counter()
    safety_layers = safety_layers or get_safety_layers()
    stage_start = time.perf_counter()
    raw_actions = llm_planner.plan(user_input)
    add_timing(timings, "llm_planning", stage_start)
    stage_start = time.perf_counter()
    parsed_actions = action_parser.parse(raw_actions)
    add_timing(timings, "action_parsing", stage_start)

    # SelfCheckGPT 保留：仅作为意图门禁的纵深防御，不再独立运行
    # （原本在此处的无条件 SelfCheckGPT 检查已移除）

    # 全局设备门禁：用户输入中若未提及任何已知设备，视为 LLM 幻觉
    stage_start = time.perf_counter()
    if safety_layers["device_gate"] and parsed_actions and not device_loader.any_device_mentioned(user_input):
        print(f"设备门禁: 用户未提及任何已知设备，丢弃 {len(parsed_actions)} 个动作")
        parsed_actions = []
    add_timing(timings, "device_gate", stage_start)

    # B02 语义意图门禁：score < 0.3 丢弃（解决"动作不匹配用户意图"）
    stage_start = time.perf_counter()
    if safety_layers["intent_gate"] and parsed_actions:
        consistent = []
        for act in parsed_actions:
            score = fact_checker.check_intent_consistency(
                user_input, act["device_id"], act["action"],
                act.get("llm_reason", "")
            )
            if score >= 0.3:
                consistent.append(act)
            # score < 0.3: 直接丢弃
        if len(consistent) < len(parsed_actions):
            print(f"意图门禁: 丢弃 {len(parsed_actions) - len(consistent)} 个不一致动作")
        parsed_actions = consistent
    add_timing(timings, "intent_gate", stage_start)

    # SelfCheckGPT 多采样一致性：仅在意图门禁通过后触发，不一致时标记需确认
    stage_start = time.perf_counter()
    if safety_layers["selfcheck"] and selfcheck_wrapper and raw_actions and parsed_actions:
        sc_result = selfcheck_wrapper.check(
            user_input, raw_actions, llm_planner.plan, num_samples=app_config.SELFCHECK_SAMPLE_COUNT,
        )
        add_timing(timings, "selfcheck", stage_start)
        if sc_result["risk_score"] >= selfcheck_wrapper.threshold:
            print(f"SelfCheckGPT: 多采样不一致 (risk={sc_result['risk_score']:.2f})")
            # 不直接 block，而是返回 require_confirm
            risk_result = no_action_risk(
                user_role, input_guard_result,
                f"selfcheck inconsistent risk={sc_result['risk_score']:.2f}",
                policy_decision="allow",
            )
            token = uuid.uuid4().hex
            conn = get_connection()
            conn.execute(
                "INSERT INTO pending_confirmations (token, user_id, user_input, user_role, input_guard_result) VALUES (?,?,?,?,?)",
                (token, user_id, user_input, user_role, json_module.dumps(input_guard_result))
            )
            conn.commit()
            conn.close()
            audit_logger.log(request_id, user_input, user_role, "", "",
                             input_guard_result,
                             {"is_valid": False, "reasons": ["selfcheck inconsistent"]},
                             {"decision": "allow", "reason": "requires confirmation"},
                             {}, "require_confirm",
                             ["selfcheck inconsistent"], risk_result)
            return SmartCommandResponse(
                request_id=request_id, user_id=user_id, user_role=user_role,
                user_input=user_input, llm_actions=raw_actions, parsed_actions=parsed_actions,
                action_results=[], overall_decision="require_confirm",
                input_guard_result=input_guard_result,
                risk_result=risk_result,
                timings_ms=finalize_timings(timings, request_start),
                require_confirmation=True, confirmation_token=token,
            )
    else:
        add_timing(timings, "selfcheck", stage_start)

    # LLM 无法识别任何设备/动作时，先用本地关键词匹配兜底
    if not parsed_actions:
        mentioned_devices = mentioned_device_ids(user_input)
        if safety_layers["device_gate"] and "让" in user_input and len(mentioned_devices) > 1:
            stage_start = time.perf_counter()
            risk_result = no_action_risk(
                user_role, input_guard_result, "cross-device delegated control"
            )
            add_timing(timings, "risk_scoring", stage_start)
            stage_start = time.perf_counter()
            audit_logger.log(request_id, user_input, user_role, "", "",
                             input_guard_result, {"is_valid": False, "reasons": ["cross-device delegated control"]},
                             {}, {}, "block", ["cross-device delegated control"], risk_result)
            add_timing(timings, "audit_logging", stage_start)
            return SmartCommandResponse(
                request_id=request_id, user_id=user_id, user_role=user_role,
                user_input=user_input, llm_actions=raw_actions, parsed_actions=[],
                action_results=[], overall_decision="block",
                input_guard_result=input_guard_result,
                risk_result=risk_result,
                timings_ms=finalize_timings(timings, request_start),
            )

        stage_start = time.perf_counter()
        fallback_actions = fallback_matcher.match(user_input)
        add_timing(timings, "fallback_matching", stage_start)
        if fallback_actions:
            parsed_actions = fallback_actions
        else:
            # 如果是查询/只读类请求，允许通过（无需生成动作）
            read_patterns = ["查看", "查询", "状态", "是多少", "怎么样", "什么", "读", "获取", "显示"]
            is_read_query = any(p in user_input for p in read_patterns)
            readable_devices = [
                device_id
                for device_id in mentioned_devices
                if device_loader.action_supported(device_id, "read")
            ]
            if is_read_query and readable_devices:
                stage_start = time.perf_counter()
                parsed_actions = [
                    {
                        "device_id": device_id,
                        "device_type": device_loader.get_device_type(device_id),
                        "action": "read",
                        "params": {},
                        "llm_reason": "read query fallback",
                    }
                    for device_id in readable_devices
                ]
                add_timing(timings, "read_fallback", stage_start)
            if not parsed_actions:
                stage_start = time.perf_counter()
                risk_result = no_action_risk(
                    user_role, input_guard_result, "no executable action recognized"
                )
                add_timing(timings, "risk_scoring", stage_start)
                stage_start = time.perf_counter()
                audit_logger.log(request_id, user_input, user_role, "", "",
                                 input_guard_result, {"is_valid": False, "reasons": ["LLM 和关键词匹配均无法识别"]},
                                 {}, {}, "block", ["未能识别任何可执行动作"], risk_result)
                add_timing(timings, "audit_logging", stage_start)
                return SmartCommandResponse(
                    request_id=request_id, user_id=user_id, user_role=user_role,
                    user_input=user_input, llm_actions=raw_actions, parsed_actions=[],
                    action_results=[], overall_decision="block",
                    input_guard_result=input_guard_result,
                    risk_result=risk_result,
                    timings_ms=finalize_timings(timings, request_start),
                )

    action_results = []
    all_passed = True
    for act in parsed_actions:
        device_id = act["device_id"]
        device_type = act["device_type"]
        action = act["action"]
        params = act.get("params", {})
        llm_reason = act.get("llm_reason", "")

        success = False
        msg = ""
        new_state = None
        transport_result = None

        stage_start = time.perf_counter()
        if safety_layers["fact_checker"]:
            is_valid, fact_risk, fact_reasons = fact_checker.check(
                device_id, action, params, user_role, llm_reason
            )
        else:
            is_valid, fact_risk, fact_reasons = True, "skipped", ["fact_checker disabled"]
        add_timing(timings, "fact_checker", stage_start)
        if not is_valid:
            msg = f"事实校验失败: {'; '.join(fact_reasons)}"
            all_passed = False
            fact_result = {"is_valid": False, "reasons": fact_reasons}
            stage_start = time.perf_counter()
            risk_result = score_action(
                user_role=user_role,
                input_guard_result=input_guard_result,
                device_loader=device_loader,
                device_id=device_id,
                device_type=device_type,
                action=action,
                params=params,
                policy_result={"decision": "block", "reason": "fact check failed"},
                physical_result={"decision": "pass", "reason": "not executed"},
                fact_result=fact_result,
                raw_actions=raw_actions,
                parsed_actions=parsed_actions,
            )
            add_timing(timings, "risk_scoring", stage_start)
            stage_start = time.perf_counter()
            audit_logger.log(request_id, user_input, user_role, device_id, action,
                             input_guard_result, fact_result,
                             {}, {}, "block", [msg], risk_result)
            add_timing(timings, "audit_logging", stage_start)
            action_results.append({
                "device_id": device_id, "action": action, "params": params,
                "policy_check": None, "physical_check": None, "fact_check": False,
                "executed": False, "final_decision": "block", "message": msg,
                "device_state_after": None,
                "risk_result": risk_result,
                "transport_result": None,
            })
            continue

        stage_start = time.perf_counter()
        if safety_layers["policy_engine"]:
            pd, pr_id, pr_reason = policy_engine.check(user_role, device_type, action)
        else:
            pd, pr_id, pr_reason = "allow", "ablation_skip", "policy_engine disabled"
        add_timing(timings, "policy_engine", stage_start)
        policy_pass = pd == "allow"
        stage_start = time.perf_counter()
        if safety_layers["physical_checker"]:
            phys_decision, phys_reason, safe_alt = physical_checker.check(device_id, action, params)
        else:
            phys_decision, phys_reason, safe_alt = "pass", "physical_checker disabled", {}
        add_timing(timings, "physical_checker", stage_start)
        phys_pass = phys_decision == "pass"

        if policy_pass and phys_pass:
            stage_start = time.perf_counter()
            success, msg, new_state, transport_result = sandbox.execute(device_id, action, params)
            add_timing(timings, "sandbox_execution", stage_start)
            final = "allow" if success else "block"
            if not success:
                all_passed = False
        else:
            success = False
            msg = f"权限: {pr_reason}" if not policy_pass else f"物理: {phys_reason}"
            final = "block"
            all_passed = False

        fact_result = {"is_valid": True}
        policy_result = {"decision": "allow" if policy_pass else "block", "reason": pr_reason}
        physical_result = {"decision": "pass" if phys_pass else "fail", "reason": phys_reason}
        stage_start = time.perf_counter()
        risk_result = score_action(
            user_role=user_role,
            input_guard_result=input_guard_result,
            device_loader=device_loader,
            device_id=device_id,
            device_type=device_type,
            action=action,
            params=params,
            policy_result=policy_result,
            physical_result=physical_result,
            fact_result=fact_result,
            raw_actions=raw_actions,
            parsed_actions=parsed_actions,
        )
        add_timing(timings, "risk_scoring", stage_start)
        action_results.append({
            "device_id": device_id, "action": action, "params": params,
            "policy_check": policy_pass, "physical_check": phys_pass, "fact_check": True,
            "executed": success, "final_decision": final, "message": msg,
            "device_state_after": new_state if success else None,
            "risk_result": risk_result,
            "transport_result": transport_result if success else None,
        })
        stage_start = time.perf_counter()
        audit_logger.log(
            request_id, user_input, user_role, device_id, action,
            input_guard_result, fact_result,
            policy_result,
            physical_result,
            final, [msg] if final == "block" else [], risk_result,
            transport_result if success else None
        )
        add_timing(timings, "audit_logging", stage_start)

    overall = "allow" if all_passed else "block"
    overall_risk = score_overall([
        result["risk_result"]
        for result in action_results
        if result.get("risk_result")
    ])
    return SmartCommandResponse(
        request_id=request_id, user_id=user_id, user_role=user_role,
        user_input=user_input, llm_actions=raw_actions, parsed_actions=parsed_actions,
        action_results=action_results, overall_decision=overall,
        input_guard_result=input_guard_result,
        risk_result=overall_risk,
        timings_ms=finalize_timings(timings, request_start),
    )


# ---------- 智能命令核心 ----------
async def process_smart_command(
    req: SmartCommandRequest,
    safety_layers: Optional[Dict[str, bool]] = None,
) -> SmartCommandResponse:
    request_start = time.perf_counter()
    timings: Dict[str, float] = {}
    safety_layers = safety_layers or get_safety_layers()
    request_id = f"SMART_{uuid.uuid4().hex[:8]}"
    stage_start = time.perf_counter()
    user_role = policy_engine.get_user_role(req.user_id)
    add_timing(timings, "user_role_lookup", stage_start)

    stage_start = time.perf_counter()
    if safety_layers["input_guard"]:
        input_guard_result = input_guard.scan(req.user_input, user_role)
    else:
        input_guard_result = {
            "prompt_injection_score": 0.0,
            "sensitive_operation": False,
            "risk_level": "low",
            "details": ["input_guard disabled"],
        }
    add_timing(timings, "input_guard", stage_start)
    input_guard_result["disabled_layers"] = disabled_layers(safety_layers)

    # high risk: 直接拒绝
    if input_guard_result["risk_level"] == "high":
        stage_start = time.perf_counter()
        risk_result = no_action_risk(
            user_role, input_guard_result, "input guard high risk"
        )
        add_timing(timings, "risk_scoring", stage_start)
        stage_start = time.perf_counter()
        audit_logger.log(request_id, req.user_input, user_role, "", "",
                         input_guard_result, {}, {}, {}, "block",
                         ["输入安全检测: 高风险"], risk_result)
        add_timing(timings, "audit_logging", stage_start)
        return SmartCommandResponse(
            request_id=request_id, user_id=req.user_id, user_role=user_role,
            user_input=req.user_input, llm_actions=[], parsed_actions=[],
            action_results=[], overall_decision="block",
            input_guard_result=input_guard_result,
            risk_result=risk_result,
            timings_ms=finalize_timings(timings, request_start),
        )

    # medium risk: 需要人工确认
    if input_guard_result["risk_level"] == "medium":
        if input_guard_result.get("sensitive_operation") and user_role in {"student", "visitor"}:
            stage_start = time.perf_counter()
            risk_result = no_action_risk(
                user_role, input_guard_result, "low-privilege sensitive operation blocked"
            )
            add_timing(timings, "risk_scoring", stage_start)
            stage_start = time.perf_counter()
            audit_logger.log(request_id, req.user_input, user_role, "", "",
                             input_guard_result, {}, {}, {}, "block",
                             ["low-privilege sensitive operation blocked"], risk_result)
            add_timing(timings, "audit_logging", stage_start)
            return SmartCommandResponse(
                request_id=request_id, user_id=req.user_id, user_role=user_role,
                user_input=req.user_input, llm_actions=[], parsed_actions=[],
                action_results=[], overall_decision="block",
                input_guard_result=input_guard_result,
                risk_result=risk_result,
                timings_ms=finalize_timings(timings, request_start),
            )

        stage_start = time.perf_counter()
        risk_result = no_action_risk(
            user_role, input_guard_result, "medium input risk requires confirmation",
            policy_decision="allow",
        )
        add_timing(timings, "risk_scoring", stage_start)
        token = uuid.uuid4().hex
        stage_start = time.perf_counter()
        conn = get_connection()
        conn.execute(
            "INSERT INTO pending_confirmations (token, user_id, user_input, user_role, input_guard_result) VALUES (?,?,?,?,?)",
            (token, req.user_id, req.user_input, user_role, json_module.dumps(input_guard_result))
        )
        conn.commit()
        conn.close()
        add_timing(timings, "confirmation_store", stage_start)
        stage_start = time.perf_counter()
        audit_logger.log(request_id, req.user_input, user_role, "", "",
                         input_guard_result, {}, {"decision": "allow", "reason": "requires confirmation"},
                         {}, "require_confirm",
                         ["medium input risk requires confirmation"], risk_result)
        add_timing(timings, "audit_logging", stage_start)
        return SmartCommandResponse(
            request_id=request_id, user_id=req.user_id, user_role=user_role,
            user_input=req.user_input, llm_actions=[], parsed_actions=[],
            action_results=[], overall_decision="require_confirm",
            input_guard_result=input_guard_result,
            risk_result=risk_result,
            timings_ms=finalize_timings(timings, request_start),
            require_confirmation=True, confirmation_token=token,
        )

    return await execute_smart_pipeline(req.user_id, req.user_input, request_id,
                                        user_role, input_guard_result, safety_layers,
                                        timings=timings, request_start=request_start)


@app.post("/api/smart_command", response_model=SmartCommandResponse)
async def smart_command(req: SmartCommandRequest, request: Request):
    return await process_smart_command(req, get_safety_layers(request))


# ---------- 人工确认 ----------
class ConfirmRequest(BaseModel):
    confirm: bool

@app.post("/api/confirm/{token}", response_model=SmartCommandResponse)
async def confirm_request(token: str, body: ConfirmRequest):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM pending_confirmations WHERE token = ? AND status = 'pending'", (token,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="待确认请求不存在或已处理")

    if not body.confirm:
        request_id = f"REJ_{uuid.uuid4().hex[:8]}"
        ig = json_module.loads(row["input_guard_result"])
        risk_result = no_action_risk(
            row["user_role"], ig, "manual confirmation rejected"
        )
        c.execute("UPDATE pending_confirmations SET status='rejected' WHERE token=?", (token,))
        conn.commit()
        conn.close()
        audit_logger.log(request_id, row["user_input"], row["user_role"], "", "",
                         ig, {}, {}, {}, "block",
                         ["manual confirmation rejected"], risk_result)
        return SmartCommandResponse(
            request_id=request_id,
            user_id=row["user_id"], user_role=row["user_role"],
            user_input=row["user_input"], llm_actions=[], parsed_actions=[],
            action_results=[], overall_decision="block",
            input_guard_result=ig,
            risk_result=risk_result,
        )

    c.execute("UPDATE pending_confirmations SET status='confirmed' WHERE token=?", (token,))
    conn.commit()
    conn.close()

    ig = json_module.loads(row["input_guard_result"])
    return await execute_smart_pipeline(row["user_id"], row["user_input"],
                                         f"CONF_{uuid.uuid4().hex[:8]}",
                                         row["user_role"], ig)


@app.get("/api/pending-confirmations")
async def list_pending():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM pending_confirmations WHERE status='pending' ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------- 策略管理 ----------
@app.get("/api/policies")
async def list_policies():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM policies")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/policies")
async def create_policy(req: PolicyCreateRequest):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""INSERT INTO policies
        (role, device_type, action_pattern, decision, priority, conditions, description, enabled)
        VALUES (?,?,?,?,?,?,?,?)""",
        (req.role, req.device_type, req.action_pattern, req.decision, req.priority,
         req.conditions, req.description, req.enabled))
    conn.commit()
    pid = c.lastrowid
    conn.close()
    return {"id": pid, "message": "策略已创建"}

@app.put("/api/policies/{policy_id}")
async def update_policy(policy_id: int, req: PolicyCreateRequest):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""UPDATE policies SET role=?, device_type=?, action_pattern=?, decision=?, priority=?,
        conditions=?, description=?, enabled=? WHERE id=?""",
        (req.role, req.device_type, req.action_pattern, req.decision, req.priority,
         req.conditions, req.description, req.enabled, policy_id))
    conn.commit()
    conn.close()
    return {"message": "策略已更新"}

@app.delete("/api/policies/{policy_id}")
async def delete_policy(policy_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM policies WHERE id=?", (policy_id,))
    conn.commit()
    conn.close()
    return {"message": "策略已删除"}


# ---------- 物理规则 ----------
@app.get("/api/physical-rules")
async def list_physical_rules():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM physical_rules")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/physical-rules")
async def create_physical_rule(req: PhysicalRuleCreateRequest):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO physical_rules (device_type, rule_type, config, description, enabled) VALUES (?,?,?,?,?)",
              (req.device_type, req.rule_type, req.config, req.description, req.enabled))
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return {"id": rid, "message": "物理规则已创建"}

@app.put("/api/physical-rules/{rule_id}")
async def update_physical_rule(rule_id: int, req: PhysicalRuleCreateRequest):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE physical_rules SET device_type=?, rule_type=?, config=?, description=?, enabled=? WHERE id=?",
              (req.device_type, req.rule_type, req.config, req.description, req.enabled, rule_id))
    conn.commit()
    conn.close()
    return {"message": "物理规则已更新"}

@app.delete("/api/physical-rules/{rule_id}")
async def delete_physical_rule(rule_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM physical_rules WHERE id=?", (rule_id,))
    conn.commit()
    conn.close()
    return {"message": "物理规则已删除"}


# ---------- 重置 ----------
@app.post("/api/reset")
async def reset_system():
    reset_db()
    return {"message": "系统已重置到初始状态"}


# ---------- 批量测试 ----------
@app.post("/api/run_tests")
async def run_tests(file: UploadFile = File(...)):
    contents = await file.read()
    try:
        test_cases = json_module.loads(contents.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="文件格式错误，必须是 JSON 数组")

    results = []
    passed_count = 0
    failed_count = 0

    for case in test_cases:
        try:
            req = SmartCommandRequest(user_id=case["user_id"], user_input=case["user_input"])
            resp = await process_smart_command(req)
            actual = resp.overall_decision
            detail = resp.model_dump()
        except Exception as e:
            actual = "error"
            detail = {"error": str(e)}

        expected = case.get("expected_decision", "allow")
        passed = actual == expected
        if passed:
            passed_count += 1
        else:
            failed_count += 1

        results.append({
            "test_id": case.get("id", ""),
            "description": case.get("description", ""),
            "passed": passed,
            "expected": expected,
            "actual": actual,
            "details": detail if actual != "error" else detail,
        })

    return {
        "total": len(test_cases),
        "passed": passed_count,
        "failed": failed_count,
        "results": results,
    }
