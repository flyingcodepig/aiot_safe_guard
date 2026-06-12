"""数据库初始化与基本操作 - 阶段3增强版"""
import json
import os
import sqlite3
from urllib.parse import unquote, urlparse

import config


def _sqlite_path(database_url: str) -> str:
    if not database_url:
        return "aiot_guard.db"
    if not database_url.startswith("sqlite:"):
        raise ValueError("Only sqlite DATABASE_URL values are supported")

    parsed = urlparse(database_url)
    if parsed.path in ("", "/"):
        return "aiot_guard.db"

    path = unquote(parsed.path)
    if parsed.netloc:
        path = f"//{parsed.netloc}{path}"
    elif path.startswith("/./") or path == "/.":
        path = path[1:]
    elif path.startswith("/") and len(path) >= 3 and path[2] == ":":
        path = path[1:]
    return os.path.normpath(path)


DB_PATH = _sqlite_path(config.DATABASE_URL)

def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """初始化数据库表，并插入默认数据"""
    conn = get_connection()
    c = conn.cursor()

    # 用户表
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT NOT NULL,
        role TEXT NOT NULL
    )''')

    # 设备表
    c.execute('''CREATE TABLE IF NOT EXISTS devices (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        capabilities TEXT
    )''')

    # 设备状态表
    c.execute('''CREATE TABLE IF NOT EXISTS device_states (
        device_id TEXT,
        key TEXT,
        value TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (device_id, key)
    )''')

    # ---------- 增强的权限策略表 ----------
    c.execute('''CREATE TABLE IF NOT EXISTS policies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL,
        device_type TEXT,
        action_pattern TEXT NOT NULL,
        decision TEXT NOT NULL,
        priority INTEGER DEFAULT 0,
        conditions TEXT,
        description TEXT,
        enabled INTEGER DEFAULT 1
    )''')

    # ---------- 增强的物理规则表 ----------
    c.execute('''CREATE TABLE IF NOT EXISTS physical_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_type TEXT NOT NULL,
        rule_type TEXT NOT NULL,
        config TEXT NOT NULL,
        description TEXT,
        enabled INTEGER DEFAULT 1
    )''')

    # 审计日志表（保持不变）
    c.execute('''CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id TEXT NOT NULL,
        user_input TEXT,
        user_role TEXT,
        target_device TEXT,
        target_action TEXT,
        input_guard_result TEXT,
        fact_check_result TEXT,
        policy_result TEXT,
        physical_result TEXT,
        final_decision TEXT,
        block_reasons TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # 待确认请求表
    c.execute('''CREATE TABLE IF NOT EXISTS pending_confirmations (
        token TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        user_input TEXT NOT NULL,
        user_role TEXT NOT NULL,
        input_guard_result TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # 速率追踪表
    c.execute('''CREATE TABLE IF NOT EXISTS rate_buckets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT NOT NULL,
        device_type TEXT NOT NULL,
        action TEXT NOT NULL,
        window_start REAL NOT NULL,
        count INTEGER DEFAULT 1
    )''')

    # 仅在首次初始化时插入种子数据（已有数据则跳过）
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] > 0:
        conn.commit()
        conn.close()
        return

    # ---------- 插入默认用户 ----------
    default_users = [
        ("u001", "张三", "student"),
        ("u002", "李四", "teacher"),
        ("u003", "王五", "admin"),
        ("u004", "访客", "visitor"),
    ]
    for user in default_users:
        c.execute("INSERT INTO users (id, username, role) VALUES (?, ?, ?)", user)

    # ---------- 插入默认策略 ----------
    default_policies = [
        ("student", "door_lock", "unlock", "block", 100, None, "学生不能打开门锁"),
        ("student", "door_lock", "lock", "allow", 50, None, "学生可以锁门"),
        ("student", "camera", "*", "block", 100, None, "学生不能操作摄像头"),
        ("student", "alarm", "*", "block", 100, None, "学生不能操作报警器"),
        ("student", "instrument", "*", "block", 100, None, "学生不能操作贵重仪器"),
        ("student", "ac", "*", "block", 100, None, "学生不能操作空调"),
        ("student", "light", "*", "allow", 50,
         json.dumps({"time_range": ["00:00", "23:59"]}),
         "学生可控制灯"),
        ("student", "fan", "*", "allow", 50, None, "学生可以控制风扇"),
        ("student", "*", "read", "allow", 10, None, "学生可以读取任何设备状态"),
        ("teacher", "*", "*", "allow", 80, None, "老师可以控制大部分设备"),
        ("teacher", "camera", "*", "block", 100, None, "老师不能操作摄像头"),
        ("teacher", "alarm", "silence", "block", 100, None, "老师不能静音报警器"),
        ("admin", "*", "*", "allow", 100, None, "管理员可以控制所有设备"),
        ("visitor", "*", "read", "allow", 110, None, "访客可以读取任何设备状态（最高优先级）"),
        ("visitor", "*", "*", "block", 100, None, "访客不能执行任何操作"),
    ]
    for policy in default_policies:
        c.execute(
            "INSERT INTO policies (role, device_type, action_pattern, decision, priority, conditions, description) VALUES (?, ?, ?, ?, ?, ?, ?)",
            policy
        )

    # ---------- 插入默认物理规则 ----------
    default_physical = [
        ("light", "range", json.dumps({"param_name": "brightness", "min_val": 1, "max_val": 100}), "亮度范围"),
        ("fan", "range", json.dumps({"param_name": "speed", "min_val": 0, "max_val": 80}), "风扇速度范围"),
        ("ac", "range", json.dumps({"param_name": "temperature", "min_val": 16, "max_val": 30}), "空调温度范围"),
        ("solder", "range", json.dumps({"param_name": "temperature", "min_val": 200, "max_val": 450}), "焊台温度范围"),
        ("*", "interlock", json.dumps({
            "condition_device": "smoke_alarm",
            "condition_state": "alarming",
            "target_device": "smoke_alarm",
            "target_action": "silence"
        }), "报警器报警时不能静音"),
        ("*", "interlock", json.dumps({
            "condition_device": "smoke_alarm",
            "condition_state": "alarming",
            "target_device": "fan_a1",
            "target_action": "turn_off"
        }), "报警器报警时不能关闭风扇"),
        ("*", "rate_limit", json.dumps({
            "max_count": 10,
            "window_seconds": 60,
            "scope": "device_type"
        }), "同一设备类型每分钟最多10次操作"),
    ]
    for rule in default_physical:
        c.execute(
            "INSERT INTO physical_rules (device_type, rule_type, config, description) VALUES (?, ?, ?, ?)",
            rule
        )

    conn.commit()
    conn.close()
    print("数据库初始化完成（已加载增强策略和物理规则）")


def reset_db():
    """重置数据库：清空动态数据，重新初始化默认数据"""
    conn = get_connection()
    c = conn.cursor()

    # 清空动态数据表
    c.execute("DELETE FROM device_states")
    c.execute("DELETE FROM audit_logs")
    # 保留用户、策略、物理规则表，但可以重新插入默认值（先删后插）
    c.execute("DELETE FROM users")
    c.execute("DELETE FROM policies")
    c.execute("DELETE FROM physical_rules")
    conn.commit()
    conn.close()

    # 重新初始化默认数据（调用 init_db 中的插入逻辑，或直接复制插入代码）
    init_db()  # 注意：init_db 会再次执行 CREATE TABLE IF NOT EXISTS，并插入默认数据

if __name__ == "__main__":
    init_db()
