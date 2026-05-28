import json
from typing import Dict, Any, Tuple, Optional
from datetime import datetime
from database import get_connection

class PolicyEngine:
    def __init__(self):
        self.cache = []

    def load_policies(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM policies WHERE enabled=1 ORDER BY priority DESC")
        rows = c.fetchall()
        conn.close()
        self.cache = []
        for row in rows:
            policy = dict(row)
            if policy['conditions']:
                try:
                    policy['conditions'] = json.loads(policy['conditions'])
                except (json.JSONDecodeError, TypeError):
                    policy['conditions'] = {}
            else:
                policy['conditions'] = {}
            self.cache.append(policy)

    def get_user_role(self, user_id: str) -> str:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        row = c.fetchone()
        conn.close()
        return row["role"] if row else "visitor"

    def evaluate_conditions(self, conditions: Dict, user_role: str, device_type: str,
                            action: str, context: Optional[Dict] = None) -> bool:
        if not conditions:
            return True

        # 时间窗口条件
        if "time_range" in conditions:
            start_str = conditions["time_range"][0]
            end_str = conditions["time_range"][1]
            try:
                start_time = datetime.strptime(start_str, "%H:%M").time()
                end_time = datetime.strptime(end_str, "%H:%M").time()
                now = datetime.now().time()
                if not (start_time <= now <= end_time):
                    return False
            except ValueError:
                return False  # 格式错误，条件视为不满足

        # 其他条件可在此扩展
        return True

    def check(self, user_role: str, device_type: str, action: str,
              context: Optional[Dict] = None) -> Tuple[str, str, str]:
        """
        返回: (decision, matched_rule_id, reason)
        decision: 'allow' / 'block' / 'require_confirm'
        """
        self.load_policies()
        for policy in self.cache:
            # 匹配角色
            if policy['role'] != '*' and policy['role'] != user_role:
                continue
            # 匹配设备类型
            if policy['device_type'] != '*' and policy['device_type'] != device_type:
                continue
            # 匹配动作
            if policy['action_pattern'] != '*' and policy['action_pattern'] != action:
                continue
            # 评估额外条件
            if not self.evaluate_conditions(policy['conditions'], user_role, device_type, action, context):
                continue
            # 命中策略
            decision = policy['decision']
            reason = policy['description'] or f"匹配策略 {policy['id']}"
            return decision, str(policy['id']), reason

        # 默认拒绝
        return "block", "default_deny", "无匹配策略，默认拒绝"