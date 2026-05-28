# 智御物联 — 项目功能说明

## 项目概述

智御物联是一个面向 AIoT（人工智能物联网）场景的多层级安全中间件系统。它部署在云端大模型（如 DeepSeek）与物理 IoT 设备之间，对自然语言生成的设备控制指令进行可信审核与执行，防止大模型幻觉、提示注入、越权操作和物理参数越界等安全风险。

## 系统架构

```
用户自然语言输入
    │
    ▼
┌──────────────────────────────────────────────────────┐
│  第一层：输入安全检测 (Input Guard)                    │
│  - LLM Guard PromptInjection 扫描器                   │
│  - 自定义禁止子串拦截                                  │
│  - IoT 敏感操作关键词感知                              │
│  - 三级风险评分: low / medium / high                   │
├──────────────────────────────────────────────────────┤
│  第二层：大模型任务规划 (LLM Planner)                  │
│  - 调用 DeepSeek 将自然语言转为结构化动作计划          │
│  - Few-shot 示例引导 + 设备别名匹配                    │
│  - 复合指令自动拆解为多动作                            │
│  - 3次温度递增重试 + 本地关键词兜底 (FallbackMatcher)   │
├──────────────────────────────────────────────────────┤
│  第三层：动作解析与事实校验 (Fact Checker)             │
│  - JSON 格式校验与修复                                 │
│  - 设备/动作存在性校验                                 │
│  - 参数类型与范围预检                                  │
│  - LLM 理由角色声明一致性校验                          │
│  - SelfCheckGPT 多采样一致性检测 (可配置开启)           │
├──────────────────────────────────────────────────────┤
│  第四层：权限与策略决策引擎 (Policy Engine)            │
│  - RBAC + ABAC 混合授权                               │
│  - 四角色: 学生/老师/管理员/访客                       │
│  - 时间窗口条件策略                                    │
│  - 优先级覆盖 + 默认拒绝                               │
├──────────────────────────────────────────────────────┤
│  第五层：物理边界与互锁校验 (Physical Checker)         │
│  - 参数范围硬约束 (range)                              │
│  - 枚举值校验                                          │
│  - 状态前置条件检查 (precondition)                     │
│  - 设备互锁规则 (interlock)                            │
│  - 速率限制 (rate_limit)                               │
├──────────────────────────────────────────────────────┤
│  第六层：仿真沙箱执行 (Sandbox Engine)                 │
│  - 虚拟设备状态机，内存+SQLite持久化                   │
│  - 统一执行接口 execute(device_id, action, params)     │
│  - 8 类 IoT 设备模拟                                   │
├──────────────────────────────────────────────────────┤
│  第七层：审计日志 (Audit Logger)                       │
│  - 全链路审计记录 (输入→LLM输出→各层决策→最终裁决)     │
│  - 统计接口 + 历史查询                                 │
│  - CSV/JSON 日志导出                                   │
└──────────────────────────────────────────────────────┘
    │
    ▼
  IoT 设备执行 / 拒绝
```

## 功能清单

### 后端核心模块

| 文件 | 功能 |
|---|---|
| `main.py` | FastAPI 入口，20+ REST API 端点，流水线编排 |
| `input_guard.py` | LLM Guard 提示注入检测 + 自定义敏感词 + 风险分级 |
| `llm_planner.py` | DeepSeek 任务规划 + Few-shot Prompt + FallbackMatcher 兜底 |
| `fact_checker.py` | 设备存在性/动作支持性/角色一致性/幻觉检测 |
| `policy_engine.py` | 基于优先级的 RBAC 策略引擎 + 时间窗口条件 |
| `physical_checker.py` | 参数范围/枚举/前置条件/互锁/速率限制五种规则 |
| `sandbox.py` | 虚拟设备状态机 |
| `audit.py` | 全链路审计日志 |
| `selfcheck_integration.py` | SelfCheckGPT 多采样一致性检测 (NLI + LLM-Prompt) |
| `device_loader.py` | YAML 设备能力库加载器 |
| `database.py` | SQLite 数据库初始化 + 7 张表 + 种子数据 |

### 模拟 IoT 设备 (8 类)

| 设备 | device_id | 类型 | 典型动作 |
|---|---|---|---|
| 实验区A智能灯1 | light_a1 | light | turn_on/off, set_brightness |
| 走廊灯1 | light_corridor1 | light | turn_on/off, set_brightness |
| 实验区A吊扇1 | fan_a1 | fan | turn_on/off, set_speed |
| 办公室门锁 | door_office | door_lock | lock, unlock |
| 恒温焊台B1 | solder_b1 | instrument | turn_on/off, set_temp |
| 烟雾报警器 | smoke_alarm | alarm | read, silence |
| 办公室摄像头 | camera_01 | camera | turn_on/off, start/stop_recording |
| 实验区A空调 | ac_a1 | ac | turn_on/off, set_temp, set_mode |

### Web 控制台

- 仪表板：统计卡片 + 饼图 + 待确认计数 + 最近日志
- 设备控制：自然语言输入 + 角色选择 + 实时安全检测结果展示
- 审计日志：筛选（按决策/角色） + CSV/JSON 导出
- 权限策略：可视化 CRUD，支持时间窗口条件
- 物理规则：管理 range/precondition/interlock/rate_limit
- 待确认：中等风险请求人工确认/拒绝队列
- 批量测试：JSON 用例上传 + 图表结果展示

### 安全评测

- 综合测试数据集：40 个用例覆盖提示注入 / 幻觉 / 越权 / 参数越界 / 互锁 / 正常操作 6 大类
- 自动化测试框架：`POST /api/run_tests` 批量执行并统计通过率
- 人工确认机制：medium 风险请求暂停等待管理员审核

### 部署支持

- Dockerfile + docker-compose.yml
- 环境变量驱动配置 (.env)
- SQLite 数据持久化

## 技术栈

- **后端**: Python 3.10 / FastAPI / SQLite / Pydantic v2
- **LLM**: DeepSeek API (via OpenAI SDK)
- **安全模型**: LLM Guard (deberta-v3-base-prompt-injection-v2)
- **前端**: Vanilla JS + Bootstrap 5 + Chart.js
- **设备配置**: YAML
- **部署**: Docker + docker-compose
