# ChatApp DevSecOps Lab

这是一个用于学习 DevSecOps 的最小后端项目，重点放在 CI/CD 安全、SAST、SCA、配置开关和容器化交付。

## 项目目标

- 提供一个可运行的 FastAPI 聊天 API
- 保留一组默认关闭的训练用不安全接口
- 让 Jenkins 流水线可以演示测试、Bandit 和 Safety 门禁
- 让你可以从“安全基线”逐步演练到“故意失败再修复”

## 本地运行

```bash
cp .env.example .env
./venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

默认模式下，不安全接口不会挂载。

如果要打开训练模式：

```bash
ENABLE_UNSAFE_ROUTES=true PYTHONPATH=. ./venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

## 核心接口

- `GET /`：服务根接口
- `GET /health`：健康检查
- `POST /messages/`：创建消息
- `GET /messages/`：获取消息列表
- `GET /messages/{message_id}`：获取消息详情
- `GET /messages/search?keyword=...`：安全搜索
- `GET /moderation/summary`：审核汇总
- `POST /unsafe_messages/`：训练用不安全写接口，仅在训练模式开放
- `GET /unsafe_search/`：训练用不安全查接口，仅在训练模式开放

## 本地验证

如果当前环境没有 `pytest`，可以先运行内置烟雾验证脚本：

```bash
PYTHONPATH=. ./venv/bin/python scripts/smoke_test.py
```

如果环境可以安装测试依赖，再运行：

```bash
PYTHONPATH=. ./venv/bin/python -m pytest -v
```

## 容器运行

```bash
docker compose up --build
```

## 学习顺序

建议先看 `docs/DEVSECOPS_LEARNING_GUIDE.md`。
