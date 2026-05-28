"""
智御物联 - AIoT安全中间件
FastAPI 主入口 (阶段4: 集成输入安全检测 + 事实校验)
"""
from contextlib import asynccontextmanager
import uuid
import os
import json as json_module
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Body
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

    device_loader = DeviceCapabilityLoader(os.getenv("DEVICE_CONFIG_DIR", "./data/devices"))
    sandbox = SandboxEngine(device_loader)
    policy_engine = PolicyEngine()
    physical_checker = PhysicalChecker(device_loader, sandbox)
    audit_logger = AuditLogger()

    model_name = os.getenv("LLM_MODEL", "deepseek-chat")
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
    llm_planner = LLMPlanner(model=model_name, api_key=api_key, base_url=base_url)
    llm_planner.build_system_prompt(device_loader)
    action_parser = ActionParser(device_loader)
    fallback_matcher = FallbackMatcher(device_loader)

    input_guard = InputGuard()
    fact_checker = FactChecker(device_loader)

    import config
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

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory="static"), name="static")


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
    }


# ---------- 直接命令 ----------
@app.post("/api/command", response_model=CommandResponse)
async def process_command(req: CommandRequest):
    request_id = f"REQ_{uuid.uuid4().hex[:8]}"
    block_reasons = []
    user_role = policy_engine.get_user_role(req.user_id)
    device_type = device_loader.get_device_type(req.device_id)

    if not device_type or device_type == "unknown":
        return CommandResponse(
            request_id=request_id, user_id=req.user_id, user_role=user_role,
            device_id=req.device_id, action=req.action, final_decision="block",
            policy_check={"decision": "fail", "reason": f"设备 {req.device_id} 不存在"},
            physical_check={"decision": "pass", "reason": ""},
            device_state_after=None, block_reasons=[f"设备 {req.device_id} 不存在"],
            message=f"设备 {req.device_id} 不存在"
        )

    pd, pr, pr2 = policy_engine.check(user_role, device_type, req.action)
    policy_result = {"decision": pd, "matched_rule": pr, "reason": pr2}
    if pd == "block":
        block_reasons.append(f"权限拒绝: {pr2}")
        audit_logger.log(request_id, req.user_input, user_role, req.device_id, req.action,
                         {}, {}, policy_result, {}, "block", block_reasons)
        return CommandResponse(
            request_id=request_id, user_id=req.user_id, user_role=user_role,
            device_id=req.device_id, action=req.action, final_decision="block",
            policy_check=policy_result, physical_check={"decision": "pass", "reason": "未执行"},
            device_state_after=None, block_reasons=block_reasons, message=f"操作被拒绝: {pr2}"
        )

    phys_decision, phys_reason, safe_alt = physical_checker.check(req.device_id, req.action, req.params or {})
    physical_result = {"decision": phys_decision, "reason": phys_reason, "safe_alternative": safe_alt}
    if phys_decision == "fail":
        block_reasons.append(f"物理边界: {phys_reason}")
        alt_msg = f"，建议值为 {safe_alt}" if safe_alt else ""
        audit_logger.log(request_id, req.user_input, user_role, req.device_id, req.action,
                         {}, {}, policy_result, physical_result, "block", block_reasons)
        return CommandResponse(
            request_id=request_id, user_id=req.user_id, user_role=user_role,
            device_id=req.device_id, action=req.action, final_decision="block",
            policy_check=policy_result, physical_check=physical_result, device_state_after=None,
            block_reasons=block_reasons, message=f"操作被拒绝: {phys_reason}{alt_msg}"
        )

    success, msg, new_state = sandbox.execute(req.device_id, req.action, req.params or {})
    if not success:
        block_reasons.append(f"执行失败: {msg}")
    final_decision = "allow" if success else "block"
    audit_logger.log(request_id, req.user_input, user_role, req.device_id, req.action,
                     {}, {}, policy_result, physical_result, final_decision, block_reasons)
    return CommandResponse(
        request_id=request_id, user_id=req.user_id, user_role=user_role,
        device_id=req.device_id, action=req.action, final_decision=final_decision,
        policy_check=policy_result, physical_check=physical_result,
        device_state_after=new_state if success else None,
        block_reasons=block_reasons, message=msg
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
async def get_logs(limit: int = 50):
    return audit_logger.get_recent_logs(limit)


# ---------- LLM 规划 ----------
@app.post("/api/llm/plan")
async def llm_plan(user_input: str):
    raw_actions = llm_planner.plan(user_input)
    parsed_actions = action_parser.parse(raw_actions)
    return {"user_input": user_input, "raw_llm_output": raw_actions, "parsed_actions": parsed_actions}


# ---------- 管道执行器（可复用） ----------
async def execute_smart_pipeline(user_id: str, user_input: str,
                                  request_id: str, user_role: str,
                                  input_guard_result: dict) -> SmartCommandResponse:
    raw_actions = llm_planner.plan(user_input)
    parsed_actions = action_parser.parse(raw_actions)

    # SelfCheckGPT 一致性检测
    if selfcheck_wrapper and raw_actions:
        sc_result = selfcheck_wrapper.check(
            user_input, raw_actions, llm_planner.plan,
            num_samples=3,
        )
        if sc_result["risk_score"] >= selfcheck_wrapper.threshold:
            return SmartCommandResponse(
                request_id=request_id, user_id=user_id, user_role=user_role,
                user_input=user_input, llm_actions=raw_actions, parsed_actions=parsed_actions,
                action_results=[], overall_decision="block",
                input_guard_result=input_guard_result,
            )

    # LLM 无法识别任何设备/动作时，先用本地关键词匹配兜底
    if not parsed_actions:
        fallback_actions = fallback_matcher.match(user_input)
        if fallback_actions:
            parsed_actions = fallback_actions
        else:
            # 如果是查询/只读类请求，允许通过（无需生成动作）
            read_patterns = ["查看", "查询", "状态", "是多少", "怎么样", "什么", "读", "获取", "显示"]
            is_read_query = any(p in user_input for p in read_patterns)
            if not is_read_query:
                audit_logger.log(request_id, user_input, user_role, "", "",
                                 input_guard_result, {"is_valid": False, "reasons": ["LLM 和关键词匹配均无法识别"]},
                                 {}, {}, "block", ["未能识别任何可执行动作"])
                return SmartCommandResponse(
                    request_id=request_id, user_id=user_id, user_role=user_role,
                    user_input=user_input, llm_actions=raw_actions, parsed_actions=[],
                    action_results=[], overall_decision="block",
                    input_guard_result=input_guard_result,
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

        is_valid, fact_risk, fact_reasons = fact_checker.check(
            device_id, action, params, user_role, llm_reason
        )
        if not is_valid:
            msg = f"事实校验失败: {'; '.join(fact_reasons)}"
            all_passed = False
            audit_logger.log(request_id, user_input, user_role, device_id, action,
                             input_guard_result, {"is_valid": False, "reasons": fact_reasons},
                             {}, {}, "block", [msg])
            action_results.append({
                "device_id": device_id, "action": action, "params": params,
                "policy_check": None, "physical_check": None, "fact_check": False,
                "executed": False, "final_decision": "block", "message": msg,
                "device_state_after": None,
            })
            continue

        pd, pr_id, pr_reason = policy_engine.check(user_role, device_type, action)
        policy_pass = pd == "allow"
        phys_decision, phys_reason, safe_alt = physical_checker.check(device_id, action, params)
        phys_pass = phys_decision == "pass"

        if policy_pass and phys_pass:
            success, msg, new_state = sandbox.execute(device_id, action, params)
            final = "allow" if success else "block"
            if not success:
                all_passed = False
        else:
            success = False
            msg = f"权限: {pr_reason}" if not policy_pass else f"物理: {phys_reason}"
            final = "block"
            all_passed = False

        action_results.append({
            "device_id": device_id, "action": action, "params": params,
            "policy_check": policy_pass, "physical_check": phys_pass, "fact_check": True,
            "executed": success, "final_decision": final, "message": msg,
            "device_state_after": new_state if success else None,
        })
        audit_logger.log(
            request_id, user_input, user_role, device_id, action,
            input_guard_result, {"is_valid": True},
            {"decision": "allow" if policy_pass else "block", "reason": pr_reason},
            {"decision": "pass" if phys_pass else "fail", "reason": phys_reason},
            final, [msg] if final == "block" else []
        )

    overall = "allow" if all_passed else "block"
    return SmartCommandResponse(
        request_id=request_id, user_id=user_id, user_role=user_role,
        user_input=user_input, llm_actions=raw_actions, parsed_actions=parsed_actions,
        action_results=action_results, overall_decision=overall,
        input_guard_result=input_guard_result,
    )


# ---------- 智能命令核心 ----------
async def process_smart_command(req: SmartCommandRequest) -> SmartCommandResponse:
    request_id = f"SMART_{uuid.uuid4().hex[:8]}"
    user_role = policy_engine.get_user_role(req.user_id)

    input_guard_result = input_guard.scan(req.user_input, user_role)

    # high risk: 直接拒绝
    if input_guard_result["risk_level"] == "high":
        audit_logger.log(request_id, req.user_input, user_role, "", "",
                         input_guard_result, {}, {}, {}, "block",
                         ["输入安全检测: 高风险"])
        return SmartCommandResponse(
            request_id=request_id, user_id=req.user_id, user_role=user_role,
            user_input=req.user_input, llm_actions=[], parsed_actions=[],
            action_results=[], overall_decision="block",
            input_guard_result=input_guard_result,
        )

    # medium risk: 需要人工确认
    if input_guard_result["risk_level"] == "medium":
        token = uuid.uuid4().hex
        conn = get_connection()
        conn.execute(
            "INSERT INTO pending_confirmations (token, user_id, user_input, user_role, input_guard_result) VALUES (?,?,?,?,?)",
            (token, req.user_id, req.user_input, user_role, json_module.dumps(input_guard_result))
        )
        conn.commit()
        conn.close()
        return SmartCommandResponse(
            request_id=request_id, user_id=req.user_id, user_role=user_role,
            user_input=req.user_input, llm_actions=[], parsed_actions=[],
            action_results=[], overall_decision="require_confirm",
            input_guard_result=input_guard_result,
            require_confirmation=True, confirmation_token=token,
        )

    return await execute_smart_pipeline(req.user_id, req.user_input, request_id,
                                        user_role, input_guard_result)


@app.post("/api/smart_command", response_model=SmartCommandResponse)
async def smart_command(req: SmartCommandRequest):
    return await process_smart_command(req)


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
        c.execute("UPDATE pending_confirmations SET status='rejected' WHERE token=?", (token,))
        conn.commit()
        conn.close()
        return SmartCommandResponse(
            request_id=f"REJ_{uuid.uuid4().hex[:8]}",
            user_id=row["user_id"], user_role=row["user_role"],
            user_input=row["user_input"], llm_actions=[], parsed_actions=[],
            action_results=[], overall_decision="block",
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