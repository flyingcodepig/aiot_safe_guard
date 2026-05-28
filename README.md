# 智御物联 — AIoT 安全中间件

面向 AIoT 场景的多层级安全中间件系统，部署在云端大模型与物理 IoT 设备之间，对 LLM 生成的控制指令进行 7 层可信审核。

```
用户输入 → 输入检测 → LLM规划 → 事实校验 → 权限决策 → 物理校验 → 仿真沙箱 → 审计
```

## 快速开始

```bash
pip install -r requirements.txt
cd backend
python modelload.py            # 首次：下载安全模型
uvicorn main:app --port 8000   # 启动服务
```

浏览器打开 http://127.0.0.1:8000/static/index.html

## 文档

- [功能说明](README_FEATURES.md) — 系统架构与完整功能清单
- [使用说明](USAGE.md) — 安装运行、API 接口、测试方法
- [进度报告](PROGRESS.md) — 开发进度、已知问题、下一步工作

## 技术栈

Python / FastAPI / SQLite / DeepSeek / LLM Guard / Bootstrap 5 / Chart.js / Docker
