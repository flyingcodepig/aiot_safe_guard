# 智御物联 — AIoT 安全中间件

> **面向 LLM-Agent 控制 AIoT 的可信指令安全网关**

当用户通过自然语言让 LLM 操控物理设备时，LLM 可能因提示注入、角色冒充、幻觉、越权、参数越界、互锁冲突等原因生成危险指令。智御物联部署在 LLM 与 IoT 设备之间，对每条控制指令进行 **7 层纵深审核**，确保只有安全、合法的指令到达物理设备。

```
用户自然语言 → InputGuard → DeviceGate → IntentGate → FactChecker
              → PolicyEngine → PhysicalChecker → SelfCheck
              → Sandbox(模拟MQTT/HTTP) → 审计日志
```

---

## 项目文件结构

```
aiot_safe_guard/
│
├── README.md                          ← 你正在看的文件
├── GOAL.md                            ← 项目长期目标与创新点
├── AGENTS.md                          ← AI Agent 工作流规范
├── BOOTSTRAP.md                       ← 新会话启动/恢复指南
├── RUNBOOK.md                         ← 命令速查手册（启动/评测/数据集）
├── CHANGELOG.md                       ← 变更日志
├── CURRENT_STATE.md                   ← 当前状态（每阶段更新）
├── NEXT_ACTIONS.md                    ← 下一步任务清单
├── SESSION_LOG.md                     ← 会话日志
├── CHECKPOINTS.md                     ← 稳定 checkpoint 记录
├── REVIEW_CHECKLIST.md                ← 双日审查清单
├── Dockerfile                         ← Docker 部署文件
├── .gitignore
├── .dockerignore
│
├── docs/                              ← 文档目录
│   ├── competition_evidence.md        ← 竞赛证据地图（数据集/指标/基线/消融）
│   ├── problem_log.md                 ← 问题日志（P001-P019，调试前先查）
│   ├── frontend_handoff.md            ← 前端交接手册（给前端开发者）
│   └── report.md                      ← 竞赛报告草稿
│
├── backend/                           ← 后端代码
│   ├── main.py                        ← FastAPI 主入口（1299 行，API 路由 + 安全管道）
│   ├── config.py                      ← 环境变量配置加载
│   ├── models.py                      ← Pydantic 数据模型
│   ├── database.py                    ← SQLite 数据库初始化/重置
│   ├── device_loader.py               ← 设备能力配置加载器
│   │
│   ├── input_guard.py                 ← 第1层：提示注入检测
│   ├── llm_planner.py                 ← LLM 任务规划器（DeepSeek）
│   ├── fact_checker.py                ← 第4层：设备/动作存在性校验
│   ├── policy_engine.py               ← 第5层：RBAC 权限策略引擎
│   ├── physical_checker.py            ← 第6层：参数范围/互锁/速率限制
│   ├── selfcheck_integration.py       ← 第7层：人工确认门控
│   ├── sandbox.py                     ← 仿真执行沙箱 + 设备状态管理
│   ├── device_driver.py               ← 模拟 MQTT/HTTP 设备驱动
│   ├── risk_scoring.py                ← 6 维 AIoT 安全风险评分
│   ├── audit.py                       ← 审计日志记录/查询/导出
│   ├── chinese_guard.py               ← 中文敏感词检测
│   ├── modelload.py                   ← LLM Guard 模型下载
│   │
│   ├── test_device_mention.py         ← 设备别名匹配测试
│   ├── test_risk_scoring.py           ← 风险评分测试
│   ├── test_selfcheck_confirmation.py ← 人工确认测试
│   ├── test_device_driver.py          ← 设备驱动测试
│   ├── test_transport_driver_api.py   ← Transport API 测试
│   │
│   ├── static/                        ← 前端静态文件
│   │   └── index.html                 ← 安全运营控制台（938 行，7 页面 SPA）
│   │
│   ├── data/devices/                  ← 设备配置文件
│   │
│   └── evaluation/                    ← 评测系统
│       ├── security_cases_core.json   ← 原始核心用例
│       ├── security_cases_expanded.json ← 扩展 182 用例
│       ├── build_expanded_cases.py    ← 扩展用例生成器
│       ├── build_formal_dataset.py    ← 正式数据集分割生成
│       ├── evaluate_security_cases.py ← 评测执行器（11 suite × 10+ 指标）
│       ├── run_eval_with_server.py    ← 全自动评测包装器
│       ├── run_eval_server.cmd        ← 手动评测服务器启动脚本
│       ├── report_eval_results.py     ← Markdown 报告生成器
│       ├── datasets/                  ← 正式分割数据集
│       │   ├── README.md              ← 数据集使用协议
│       │   ├── security_cases_core_regression.json   ← 182 核心回归
│       │   ├── security_cases_dev.json               ← 1000 开发集
│       │   ├── security_cases_validation.json        ← 500 验证集
│       │   ├── security_cases_final_test.json        ← 2000 冻结测试集
│       │   ├── security_cases_formal_all.json        ← 3682 全量
│       │   └── security_cases_formal_manifest.json   ← SHA-256 清单
│       └── results/                   ← 评测结果（JSON + Markdown）
│           ├── latest_eval.json       ← 最新 11-suite 快照
│           ├── latest_eval.md         ← 最新报告（可直接用于竞赛报告）
│           ├── core_full_isolated.json/.md    ← 核心集隔离评测
│           ├── validation_full_isolated.json/.md ← 验证集隔离评测
│           └── final_test_full.json/.md       ← 冻结最终测试
│
└── somethingelse/                     ← 非核心工作区材料（venv 等）
```

---

## 快速开始

### 环境要求

- Python 3.10+
- Windows / Linux / macOS

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`（或直接编辑 `backend/.env`）：

```env
# LLM API（使用 DeepSeek 或其他 OpenAI 兼容 API）
OPENAI_API_KEY=your-api-key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat

# 数据库
DATABASE_URL=sqlite:///./aiot_guard.db

# 安全层开关（在线模式全部启用）
ENABLE_LLM_PLANNER=true
ENABLE_LLM_FACT_CHECKS=true
ENABLE_LLM_GUARD_SCANNER=true
SELFCHECK_ENABLED=true

# API 认证
API_KEY=aiot-dev-key-change-in-production
```

### 3. 下载安全模型（可选，首次）

```bash
cd backend
python modelload.py
```

### 4. 启动服务

```bash
cd backend
uvicorn main:app --host 127.0.0.1 --port 8000
```

浏览器打开 `http://127.0.0.1:8000`，进入安全运营控制台。

---

## 使用指南

### 前端控制台

控制台提供 7 个页面：

| 页面 | 功能 |
|------|------|
| **仪表板** | 系统概览：请求统计、拦截率、风险分布图表、近期日志 |
| **设备控制** | 核心页面：自然语言输入 → 查看完整 7 层安全决策链路 |
| **审计日志** | 历史记录查询/筛选/CSV导出/JSON导出 + 审计回放 |
| **权限策略** | RBAC 策略 CRUD 管理 |
| **物理规则** | 互锁/范围/速率限制规则管理 |
| **待确认** | 需要人工确认的高风险请求列表 |
| **批量测试** | 上传安全用例 JSON 文件批量测试 |

### API 接口

Base URL: `http://127.0.0.1:8000`

所有 POST/PUT/DELETE 需携带 `X-API-Key` 请求头。

```http
# 核心指令
POST /api/smart_command     ← 自然语言指令 → 7 层安全审核 → 决策

# 查询
GET  /health                ← 系统健康检查（无需 API Key）
GET  /api/stats             ← 请求统计
GET  /api/devices           ← 设备列表与状态
GET  /api/logs              ← 审计日志（支持筛选）
GET  /api/pending-confirmations ← 待确认请求
GET  /api/eval_results      ← 最新评测结果（无需 API Key）

# 操作
POST /api/reset             ← 重置系统状态
POST /api/confirm/:token    ← 人工确认/拒绝
POST /api/device/:id/set_state ← 设置设备状态

# 管理
GET/POST /api/policies      ← 权限策略管理
PUT/DELETE /api/policies/:id
GET/POST /api/physical-rules ← 物理规则管理
PUT/DELETE /api/physical-rules/:id

# 导出
GET  /api/logs/export?format=csv|json  ← 审计日志导出

# 评测
POST /api/run_tests         ← 上传安全用例 JSON 批量测试
```

完整 API 响应结构见 `docs/frontend_handoff.md` 第 3 节。

### 命令行评测

```bash
cd backend

# 快速评测（核心 182 用例，全系统）
python evaluation/run_eval_with_server.py \
    --cases evaluation/security_cases_expanded.json \
    --output evaluation/results/latest_eval.json \
    --request-timeout 8

# 11 套件完整评测（全系统 + 4 基线 + 6 消融）
python evaluation/run_eval_with_server.py \
    --cases evaluation/security_cases_expanded.json \
    --output evaluation/results/latest_eval.json \
    --request-timeout 8

# 验证集隔离评测（必须 --reset-each-case）
python evaluation/run_eval_with_server.py \
    --cases evaluation/datasets/security_cases_validation.json \
    --output evaluation/results/validation_full_isolated.json \
    --ablation full --reset-each-case --request-timeout 8

# 生成 Markdown 报告
python evaluation/report_eval_results.py \
    --input evaluation/results/latest_eval.json \
    --output evaluation/results/latest_eval.md
```

### 数据集操作

```bash
cd backend

# 重新生成扩展用例
python evaluation/build_expanded_cases.py

# 重新生成正式数据集分割
python evaluation/build_formal_dataset.py \
    --output-dir evaluation/datasets \
    --seed 20260612 \
    --dev-count 1000 \
    --validation-count 500 \
    --final-count 2000
```

### 运行测试

```bash
cd backend
python test_device_mention.py
python test_risk_scoring.py
python test_selfcheck_confirmation.py
python test_device_driver.py
python test_transport_driver_api.py
```

---

## 离线评测模式

用于无 LLM API 环境的快速评测（评测脚本自动配置）：

| 环境变量 | 离线值 | 说明 |
|---------|--------|------|
| `ENABLE_LLM_PLANNER` | `false` | 禁用 LLM 规划 |
| `ENABLE_LLM_FACT_CHECKS` | `false` | 禁用 LLM 事实校验 |
| `ENABLE_LLM_GUARD_SCANNER` | `false` | 禁用 LLM 扫描器 |
| `SELFCHECK_ENABLED` | `false` | 禁用 SelfCheck |
| `LLM_TIMEOUT_SECONDS` | `0.5` | 快速失败 |
| `LLM_MAX_RETRIES` | `0` | 不重试 |

离线模式仍能验证 7 层安全管道中的 5 层确定性逻辑（InputGuard 关键词部分、DeviceGate、FallbackMatcher、PolicyEngine、PhysicalChecker）以及完整的数据集/指标/报告管线。

---

## 关键文档索引

| 你想做什么 | 读这个 |
|-----------|--------|
| 了解项目目标和创新点 | `GOAL.md` |
| 看当前状态和已知问题 | `CURRENT_STATE.md` |
| 找下一步要做的任务 | `NEXT_ACTIONS.md` |
| 恢复上次会话 | `BOOTSTRAP.md` → `SESSION_LOG.md` |
| 运行命令速查 | `RUNBOOK.md` |
| 调试前查已知问题 | `docs/problem_log.md`（按 P001-P019 索引） |
| 了解竞赛证据现状 | `docs/competition_evidence.md` |
| 前端开发 | `docs/frontend_handoff.md` |
| 写竞赛报告 | `docs/report.md` |

---

## 技术栈

| 层 | 技术 |
|----|------|
| 后端框架 | FastAPI (Python) |
| 数据库 | SQLite (WAL 模式) |
| LLM | DeepSeek (OpenAI 兼容 API) |
| 前端 | Bootstrap 5 + Chart.js + Vanilla JS |
| 评测 | 自建 3682 条正式数据集 + 11-suite 自动化管道 |
| 安全模型 | LLM Guard (PromptInjection) |
| 部署 | Uvicorn / Docker |

---

## 竞赛定位

本项目定位为**信安赛一等奖**级别的参赛作品：

- **3 个命名创新点**：语义一致性幻觉门禁、RBAC-物理约束融合决策引擎、多层审计与人工确认
- **3682 条正式评测数据集**（train/dev/val/test 分离，SHA-256 清单）
- **11 套件评测**：全系统 + 4 基线 + 6 消融
- **10+ 评测指标**：含安全正确率（safety_correct_rate）和决策不匹配分类
- **完整审计闭环**：风险评分 + 日志 + CSV/JSON 导出 + 回放
- **模拟设备闭环**：MQTT/HTTP 驱动 + transport_result

详见 `docs/competition_evidence.md`。
