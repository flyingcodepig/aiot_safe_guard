"""审计日志记录"""
import json
from datetime import datetime
from database import get_connection

class AuditLogger:
    def __init__(self):
        pass

    def log(self, request_id: str, user_input: str, user_role: str,
            device_id: str, action: str, input_guard: dict,
            fact_check: dict, policy_result: dict, physical_result: dict,
            final_decision: str, block_reasons: list):
        """记录完整审计日志"""
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            """INSERT INTO audit_logs
            (request_id, user_input, user_role, target_device, target_action,
             input_guard_result, fact_check_result, policy_result, physical_result,
             final_decision, block_reasons, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                request_id,
                user_input,
                user_role,
                device_id,
                action,
                json.dumps(input_guard, ensure_ascii=False),
                json.dumps(fact_check, ensure_ascii=False),
                json.dumps(policy_result, ensure_ascii=False),
                json.dumps(physical_result, ensure_ascii=False),
                final_decision,
                json.dumps(block_reasons, ensure_ascii=False),
                datetime.now().isoformat()
            )
        )
        conn.commit()
        conn.close()

    def get_recent_logs(self, limit: int = 50):
        """获取最近的审计日志"""
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_stats(self):
        """获取统计信息"""
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as total FROM audit_logs")
        total = c.fetchone()["total"]

        c.execute("SELECT COUNT(*) as blocked FROM audit_logs WHERE final_decision='block'")
        blocked = c.fetchone()["blocked"]

        c.execute("SELECT COUNT(*) as allowed FROM audit_logs WHERE final_decision='allow'")
        allowed = c.fetchone()["allowed"]

        conn.close()
        return {"total": total, "blocked": blocked, "allowed": allowed}