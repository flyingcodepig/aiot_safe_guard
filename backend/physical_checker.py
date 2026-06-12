import json
import time
from typing import Dict, Any, Tuple, List
from database import get_connection
from device_loader import DeviceCapabilityLoader
from sandbox import SandboxEngine

class PhysicalChecker:
    def __init__(self, device_loader: DeviceCapabilityLoader, sandbox: SandboxEngine):
        self.device_loader = device_loader
        self.sandbox = sandbox

    def check(self, device_id: str, action: str, params: Dict[str, Any]) -> Tuple[str, str, Dict]:
        """
        返回: (decision, reason, safe_alternative)
        decision: 'pass' / 'fail'
        """
        if not self.device_loader.device_exists(device_id):
            return "fail", f"设备 {device_id} 不存在", {}

        device = self.device_loader.get_device(device_id)

        # 1. 基于设备能力库的参数范围检查
        for param_name, param_value in params.items():
            if param_name in device.attributes:
                attr = device.attributes[param_name]
                if 'range' in attr and isinstance(param_value, (int, float)):
                    min_val, max_val = attr['range']
                    if param_value < min_val or param_value > max_val:
                        safe_val = max(min_val, min(param_value, max_val))
                        return "fail", f"参数 {param_name}={param_value} 超出范围 [{min_val}, {max_val}]", {param_name: safe_val}

        # 2. 从数据库加载并执行物理规则
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM physical_rules WHERE enabled=1 AND device_type IN (?, '*')",
                  (device.type,))
        rules = c.fetchall()
        conn.close()

        for rule in rules:
            config = json.loads(rule['config'])
            rtype = rule['rule_type']

            if rtype == 'range':
                # 数据库中的范围规则作为补充（若已通过设备能力检查则一般不会失败）
                param_name = config.get('param_name')
                if param_name and param_name in params:
                    param_val = params[param_name]
                    if 'min_val' in config and 'max_val' in config:
                        if isinstance(param_val, (int, float)):
                            if param_val < config['min_val'] or param_val > config['max_val']:
                                safe = max(config['min_val'], min(param_val, config['max_val']))
                                return "fail", f"参数 {param_name}={param_val} 超出范围 [{config['min_val']}, {config['max_val']}]", {param_name: safe}
                    elif 'allowed_values' in config:
                        if param_val not in config['allowed_values']:
                            return "fail", f"参数 {param_name}={param_val} 不在允许的枚举值中", {}

            elif rtype == 'precondition':
                cond_device = config.get('condition_device')
                cond_state = config.get('condition_state')
                if cond_device and cond_state:
                    state = self.sandbox.get_device_state(cond_device)
                    # 根据设备类型，状态可能存储在 'status' 或其它属性中，这里默认使用 'status'
                    current_cond = state.get('status', '')
                    if str(current_cond) != str(cond_state):
                        return "fail", f"前置条件不满足: {rule['description']}", {}

            elif rtype == 'interlock':
                # 当条件设备处于指定状态时，禁止对目标设备执行目标动作
                cond_device = config.get('condition_device')
                cond_state = config.get('condition_state')
                target_device = config.get('target_device')
                target_action = config.get('target_action')
                if (cond_device and cond_state and
                    target_device == device_id and target_action == action):
                    state = self.sandbox.get_device_state(cond_device)
                    current_cond = state.get('status', '')
                    if str(current_cond) == str(cond_state):
                        return "fail", f"互锁冲突: {rule['description']}", {}

            elif rtype == 'rate_limit':
                max_count = config.get('max_count', 5)
                window_seconds = config.get('window_seconds', 60)
                scope = config.get('scope', 'device')
                match_id = device_id if scope == 'device' else device.type
                now = time.time()
                cutoff = now - window_seconds

                conn2 = get_connection()
                c2 = conn2.cursor()
                c2.execute("DELETE FROM rate_buckets WHERE window_start < ?", (cutoff,))
                if scope == 'device':
                    c2.execute("SELECT SUM(count) as total FROM rate_buckets WHERE device_id = ? AND action = ? AND window_start >= ?",
                               (match_id, action, cutoff))
                else:
                    c2.execute("SELECT SUM(count) as total FROM rate_buckets WHERE device_type = ? AND action = ? AND window_start >= ?",
                               (match_id, action, cutoff))
                row = c2.fetchone()
                current = row["total"] if row["total"] else 0
                if current >= max_count:
                    conn2.close()
                    return "fail", f"速率限制: {scope}={match_id} 的 {action} 在{window_seconds}s内已达{current}次 (上限{max_count})", {}
                c2.execute("INSERT INTO rate_buckets (device_id, device_type, action, window_start, count) VALUES (?,?,?,?,1)",
                           (device_id, device.type, action, now))
                conn2.commit()
                conn2.close()

        return "pass", "物理检查通过", {}
