# AIoT Safe Guard 前端交接手册

## 写给接手前端的人

这份文档告诉你：项目是什么、现在前端长什么样、后端有哪些 API、要建成什么风格、以及怎么用 Claude Code 的 Skill 来加速搭建。

---

## 1. 项目定位（一句话）

**面向 LLM-Agent 控制 AIoT 的可信指令安全网关** — 一个安全运营控制台，不是普通的 IoT 仪表盘。

用户在输入框里用自然语言说"打开走廊灯"，系统经过 7 层安全检测后决定是否放行、拦截还是要求人工确认。前端要展示这整个决策链路。

---

## 2. 当前前端状态

**文件位置：** `backend/static/index.html`（938 行，单文件）

**技术栈：**
- Bootstrap 5.3 CSS（CDN）
- Bootstrap Icons（CDN）
- Chart.js 4.4（CDN，仅用于仪表盘饼图）
- 零构建工具，零框架，原生 JS

**已有 7 个页面（单页 SPA，sidebar 切换）：**

| 页面 | 数据来源 | 当前状态 |
|------|---------|---------|
| 仪表板 | `/api/stats` + `/api/logs` | 有统计卡片 + 饼图 + 近期日志表，功能完整但简陋 |
| 设备控制 | `/api/smart_command` + `/api/devices` | **核心页面**，自然语言输入 + 安全决策链路展示 + 设备状态卡片 |
| 审计日志 | `/api/logs` + `/api/logs/export` | 表格 + 筛选 + CSV/JSON 导出 + 审计回放 Modal |
| 权限策略 | `/api/policies` | CRUD 表格 + Modal 表单 |
| 物理规则 | `/api/physical-rules` | CRUD 表格 + Modal 表单 |
| 待确认 | `/api/pending-confirmations` + `/api/confirm/:token` | 人工确认列表 + 确认/拒绝按钮 |
| 批量测试 | `/api/run_tests` | 文件上传 + 结果饼图 + 明细表 |

**核心渲染函数（不要删）：**
- `renderSmartCommandTrace(resp)` — 安全决策链路可视化（257 行，最核心）
- `renderRiskSummary(risk)` — 风险评分环形图 + 因子列表
- `renderRiskComponents(risk)` — 6 维风险分量进度条
- `renderTransportResult(transport)` — MQTT/HTTP 协议握手展示
- `renderAuditReplay(log)` — 审计回放 Modal（7 层决策时间线）
- `renderPlanTrace(resp)` — LLM 计划 vs 解析动作对比

---

## 3. 后端 API 全部端点

Base URL：前端通过相对路径访问（同源部署，FastAPI 同时 serve 静态文件）

### 3.1 核心指令接口

```http
POST /api/smart_command
Content-Type: application/json

{
  "user_id": "u001",          // u001=学生 u002=老师 u003=管理员 u004=访客
  "user_input": "打开走廊灯，把风扇调到50"
}
```

**响应结构（这是前端需要渲染的核心数据）：**

```json
{
  "request_id": "SMART_a1b2c3d4",
  "user_id": "u001",
  "user_role": "student",
  "user_input": "打开走廊灯，把风扇调到50",
  "overall_decision": "allow|block|require_confirm",
  "require_confirmation": true|false,
  "confirmation_token": "CONFIRM_xxxxxxxx",

  "input_guard_result": {
    "prompt_injection_score": 0.0,
    "sensitive_operation": false,
    "risk_level": "low|medium|high",
    "details": ["..."],
    "disabled_layers": []
  },

  "llm_actions": [
    {"device_id": "light_corridor", "action": "turn_on", "params": {}, "reason": "..."}
  ],

  "parsed_actions": [
    {"device_id": "light_corridor", "action": "turn_on", "params": {}}
  ],

  "action_results": [
    {
      "device_id": "light_corridor",
      "action": "turn_on",
      "params": {},
      "final_decision": "allow|block",
      "message": "执行成功",
      "fact_check": true,
      "policy_check": true,
      "physical_check": true,
      "risk_result": { "score": 25.0, "level": "low", "components": [...], "top_factors": [...] },
      "transport_result": {
        "protocol": "mqtt|http",
        "endpoint": "aiot/light/light_corridor/command",
        "method": "publish|POST",
        "payload": {"action": "turn_on"},
        "ack": {"status": "ok"},
        "latency_ms": 2.35,
        "simulated": true
      },
      "device_state_after": {"power": "on", "brightness": 80}
    }
  ],

  "risk_result": {
    "score": 25.0,
    "level": "low|medium|high|critical",
    "strategy": "max_action_score|fallback_no_action",
    "action_count": 1,
    "top_factors": [
      {"name": "device_criticality", "score": 25.0, "reason": "device_type=light"}
    ],
    "components": [
      {"name": "input_risk", "score": 10.0, "reason": "..."},
      {"name": "device_criticality", "score": 25.0, "reason": "..."},
      {"name": "permission_risk", "score": 65.0, "reason": "..."},
      {"name": "parameter_risk", "score": 0.0, "reason": "..."},
      {"name": "physical_interlock_risk", "score": 10.0, "reason": "..."},
      {"name": "model_consistency_risk", "score": 10.0, "reason": "..."}
    ]
  },

  "timings_ms": {
    "user_role_lookup": 0.5,
    "input_guard": 0.2,
    "llm_planning": 0.0,
    "action_parsing": 0.1,
    "device_gate": 0.1,
    "intent_gate": 0.1,
    "selfcheck": 0.0,
    "fallback_matching": 0.0,
    "fact_checker": 0.1,
    "policy_engine": 0.3,
    "physical_checker": 0.5,
    "sandbox_execution": 2.0,
    "risk_scoring": 0.1,
    "audit_logging": 1.0,
    "total": 5.0
  }
}
```

### 3.2 其他端点速查

```http
GET  /health                              → {"status":"ok","database":"ok","loaded_devices":8,"version":"4.0.0"}
POST /api/reset                           → 重置系统状态
GET  /api/stats                           → {"total":N,"blocked":N,"allowed":N}
GET  /api/devices                         → {"devices":[{device_id,type,name,state,actions,aliases}]}
POST /api/device/:id/set_state            → {"key":"power","value":"on"}  设置设备状态
GET  /api/logs?limit=200&final_decision=block&user_role=student
GET  /api/logs/export?format=csv|json&limit=10000
GET  /api/pending-confirmations           → [{token,user_id,user_role,user_input,created_at}]
POST /api/confirm/:token                  → {"confirm":true}  确认执行 / {"confirm":false}  拒绝
GET  /api/policies                        → [{id,role,device_type,action_pattern,decision,priority,conditions,description}]
POST /api/policies                        → 创建策略
PUT  /api/policies/:id                    → 更新策略
DELETE /api/policies/:id                  → 删除策略
GET  /api/physical-rules                  → [{id,device_type,rule_type,config,description}]
POST /api/physical-rules                  → 创建物理规则
PUT  /api/physical-rules/:id              → 更新规则
DELETE /api/physical-rules/:id            → 删除规则
POST /api/run_tests                       → multipart/form-data, file=安全用例JSON
```

**认证：** 所有 POST/PUT/DELETE 需要 `X-API-Key: aiot-dev-key-change-in-production` 请求头。GET 路由除了 `/health`、`/static/*`、`/api/eval_results` 外也需要 API Key。

**⚠️ 重要：** 当前 `apiGet()` 函数没有发送 X-API-Key，如果后端 `API_KEY` 配置非空会导致 GET 请求 401。接手者需要修改 `apiGet()`：
```js
async function apiGet(url) {
    const res = await fetch(API_BASE + url, {
        headers: { 'X-API-Key': 'aiot-dev-key-change-in-production' }
    });
    if (!res.ok) throw new Error(`请求失败: ${res.status}`);
    return res.json();
}
```

---

## 4. 设计方向（由 Claude Code Skill 驱动）

### 4.1 已安装的 Skill

接手者请在 Claude Code 中确认以下 Skill 已启用：

```bash
claude plugin list
```

应该看到：
- `frontend-design@claude-plugins-official` — 美学方向选择，拒绝 AI 味设计
- `interface-design@interface-design` — 仪表盘/管理面板专用，暗色主题 token 系统

如果没装，运行：
```bash
claude plugin install frontend-design@claude-plugins-official
claude plugin marketplace add Dammyjay93/interface-design
claude plugin install interface-design@interface-design
```

### 4.2 视觉方向（给接手者的 prompt）

在 Claude Code 中运行：

```
/interface-design:init
```

然后告诉 Claude：

> 我要构建一个 **AIoT 安全运营控制台**（Security Operations Dashboard for IoT safety gateway）。
> 风格方向：**Dark OLED Luxury + Precision & Density**
> - 真正的深色背景（#0a0e14 到 #12171f），不是灰色
> - 冷色调强调色（青色、蓝绿色、电蓝色）
> - 数据/指标用等宽字体，标签用无衬线
> - 3 层表面立面（card → elevated card → modal）
> - 高数据密度，清晰的视觉层级
> - 所有交互元素 focus-visible 环 ≥ 3:1 对比度
> - WCAG AA 最低要求

### 4.3 设计提取（从现有代码学）

现有 `index.html` 中需要保留的设计资产：
- 风险评分圆环 (`.risk-score`) — 92px 圆形，颜色按 risk level 变化
- 安全决策链路步骤 (`.trace-step`) — 左边框颜色表示通过/拦截/警告
- 风险分量进度条 (`.component-bar`) — 细横条，按分数着色
- 设备卡片 (`.device-card`) — hover 上浮效果
- 风险等级颜色映射：`low→#198754 green`, `medium→#ffc107 yellow`, `high→#dc3545 red`, `critical→#212529 black`

---

## 5. 需要重建/新增的页面规格

### 5.1 仪表板（Dashboard）— 重做

**当前问题：** 4 个统计卡 + 一个饼图 + 日志表，太简陋。

**目标：**
```
┌─────────────────────────────────────────────────────┐
│  [系统健康]  [总请求数]  [拦截率]  [待确认数]         │  ← 4 个 KPI 卡
│  [安全干预率]  [平均延迟]  [设备在线]  [风险评分]     │  ← 再加 4 个
├────────────────────┬────────────────────────────────┤
│  拦截/放行趋势      │  风险等级分布（环形图）          │
│  (折线图/面积图)    │  low/medium/high/critical       │
├────────────────────┼────────────────────────────────┤
│  7 层安全链路       │  最新 5 条告警/拦截              │
│  可视化流程图        │  (高风险的拦截 + 待确认)         │
│  (Sankey/流程)     │                                │
├────────────────────┴────────────────────────────────┤
│  设备状态总览（8 个设备卡片，实时状态）                 │
└─────────────────────────────────────────────────────┘
```

**数据来源：** `/api/stats` + `/api/logs?limit=50` + `/api/devices` + `/api/pending-confirmations`

### 5.2 设备控制（Command Center）— 保留核心逻辑，重做 UI

**当前问题：** 功能完整但视觉不专业。

**目标：**
- 输入区保持简洁（输入框 + 用户选择 + 发送按钮）
- **安全决策链路** 改为时间线/流程图风格（目前在 `renderSmartCommandTrace` 中，逻辑保留，CSS 全部重写）
- 每层决策展开/折叠（InputGuard → DeviceGate → IntentGate → FactChecker → PolicyEngine → PhysicalChecker → SelfCheck）
- 风险评分大圆环放在决策链顶部
- 风险分量以雷达图或水平条形图展示
- MQTT/HTTP 协议握手以代码块 + 协议标签展示
- 设备状态变更前后对比

### 5.3 审计日志（Audit Log）— 重做

**当前问题：** Bootstrap table，没有视觉层次。

**目标：**
- 暗色主题表格，行按决策类型着色（allow=绿底, block=红底, confirm=黄底）
- 筛选器改为标签/chip 风格
- 审计回放 Modal 重做：7 层决策时间线（垂直步骤），每层有 icon + 状态色 + 详情展开
- 风险评分嵌入每行

### 5.4 评估证据（Evaluation Evidence）— **新增**

这是竞赛报告的核心证据页面，目前完全缺失。

**目标：**
- 从 `backend/evaluation/results/latest_eval.json` 加载数据（需要后端新增一个 `/api/eval_results` 端点来 serve 这个 JSON）
- 套件对比表（11 suites × 指标，可排序、可搜索）
- 消融实验对比图（分组柱状图，展示每层消融后的攻击拦截率下降）
- 威胁类型分布（堆叠柱状图或热力图）
- 模块耗时分布（箱线图或瀑布图）
- 高风险拦截案例表（从 `latest_eval.json` 的 high-risk blocked cases 加载）

**需要后端新增的端点：**
```http
GET /api/eval_results   →  返回 latest_eval.json 的内容
```
（简单实现：在 `main.py` 加一个路由读 `evaluation/results/latest_eval.json` 并返回 JSON）

### 5.5 系统架构（System Architecture）— **新增**

**目标：**
- 静态页面，展示系统架构图（SVG）
- 7 层安全管道流程图
- 数据流：用户输入 → API → 各安全层 → 决策 → 设备/审计
- 设备拓扑示意（8 个设备的连接关系）

---

## 6. 使用 Claude Code Skill 的工作流

### 6.1 启动设计系统

```bash
# 第一步：初始化设计系统
/interface-design:init
# 告诉 Claude 你的方向（Dark OLED + Precision Density + 安全运营控制台）

# 第二步：提取现有设计资产
/interface-design:extract backend/static/index.html
# 保留 .risk-score, .trace-step, .component-bar 的设计基因

# 第三步：检查设计系统状态
/interface-design:status
# 查看当前 tokens、patterns、direction
```

### 6.2 逐个页面搭建

对每个页面，按这个流程：

```bash
# 1. 让 Claude 出设计方案
/frontend-design 我要重建 [页面名]，这是 [用途]，用户是 [角色]

# 2. 让 Claude 写代码实现
# 3. 用 interface-design:critique 审查
/interface-design:critique
# 4. 用 interface-design:audit 检查一致性
/interface-design:audit
```

### 6.3 推荐的 prompt 模板

```
/frontend-design

为 AIoT Safe Guard 安全网关构建 [页面名称]。

## 上下文
- 项目定位：面向 LLM-Agent 控制 AIoT 的可信指令安全网关
- 目标用户：安全运维人员、竞赛评委
- 后端 API：见 docs/frontend_handoff.md 第 3 节
- 现有代码：backend/static/index.html 中的 renderXxx() 函数

## 设计要求
- 暗色 OLED 主题（背景 #0a0e14）
- 高数据密度，清晰视觉层级
- 等宽字体用于数据/指标，无衬线用于标签
- 3 层表面立面
- 冷色调强调色（青、蓝绿、电蓝）
- WCAG AA 对比度

## 这个页面需要展示
[具体的数据和交互描述]
```

---

## 7. 技术约束与提示

### 7.1 必须保留的
- `API_BASE = ''` — 相对路径，同源部署
- `apiGet()` / `apiPost()` / `apiDelete()` — 已有的 HTTP 封装
- `renderSmartCommandTrace()` — 安全决策链路渲染逻辑
- `renderRiskSummary()` / `renderRiskComponents()` — 风险评分渲染
- `renderTransportResult()` — 协议握手渲染
- `renderAuditReplay()` — 审计回放渲染
- `showAuditReplay()` / `confirmPending()` / `resetSystem()` / `sendCommand()` — 全局函数

### 7.2 可以改的
- 所有 CSS（建议从零重写，不用 Bootstrap 默认主题）
- HTML 结构（但保留 sidebar 导航 + page-content 容器架构）
- 图表库（可以从 Chart.js 换成 ECharts，CDN 引用即可）
- 字体（建议 Fira Code / JetBrains Mono 用于数据，Inter / Noto Sans SC 用于中文）

### 7.3 不要做的
- 不要引入 React/Vue 等框架（保持零构建工具）
- 不要删除任何 `renderXxx()` 函数（后端 API 响应结构不变）
- 不要改 API 端点路径
- 不要改 `X-API-Key` 认证方式
- 不要删除 Chart.js（仪表盘和批量测试在用）

### 7.4 关于文件拆分
如果单文件 938 行太难维护，可以拆成：
```
backend/static/
  index.html          ← 入口（导航 + 页面容器）
  css/
    dashboard.css     ← 暗色主题样式
  js/
    api.js            ← apiGet/apiPost/apiDelete
    render-risk.js    ← renderRiskSummary/Components/Badge
    render-trace.js   ← renderSmartCommandTrace/PlanTrace/TransportResult/AuditReplay
    pages/
      dashboard.js
      devices.js
      logs.js
      policies.js
      rules.js
      pending.js
      testing.js
      eval.js         ← 新增
      architecture.js ← 新增
```
用 `<script src="..."></script>` 引入，无需打包工具。

---

## 8. 后端启动（前端调试用）

```powershell
cd D:\aiot_safe_guard\backend
$env:SELFCHECK_ENABLED='false'
$env:ENABLE_LLM_GUARD_SCANNER='false'
$env:ENABLE_LLM_PLANNER='false'
$env:ENABLE_LLM_FACT_CHECKS='false'
$env:DATABASE_URL='sqlite:///./aiot_guard.db'
..\somethingelse\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

浏览器打开 `http://127.0.0.1:8000` 即可看到前端。

默认 API Key：`aiot-dev-key-change-in-production`（在 `backend/.env` 里）

---

## 9. 参考材料

- 项目目标与创新点：`GOAL.md`
- 竞赛证据地图：`docs/competition_evidence.md`
- 评测运行手册：`RUNBOOK.md`
- 后端 API 全定义：`backend/main.py`（1299 行）
- 风险评分算法：`backend/risk_scoring.py`（239 行）
- 策略引擎：`backend/policy_engine.py`（83 行）
- 物理检查器：`backend/physical_checker.py`（109 行）
- 模拟设备驱动：`backend/device_driver.py`（101 行）
- 标杆报告 PDF：`信安赛作品报告.pdf`（57 页，可参考其前端截图风格）

---

## 10. 快速启动 Checklist

- [ ] 确认 `frontend-design` 和 `interface-design` 两个 Skill 已安装
- [ ] 运行 `/interface-design:init` 初始化设计系统
- [ ] 跑通后端，浏览器打开 `http://127.0.0.1:8000` 确认现有前端可用
- [ ] 用 `/frontend-design` 逐个页面重建
- [ ] 每个页面用 `/interface-design:critique` 审查
- [ ] 全站用 `/interface-design:audit` 检查一致性
- [ ] 截图放进报告
