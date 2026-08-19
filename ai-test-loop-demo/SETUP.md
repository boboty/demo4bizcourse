# 环境搭建（现场演示用）

目标：换一台机器，5 分钟内跑到 `SMOKE STATUS: READY`。演示当天不需要联网。

## 已知限制（先看这个）

`vendor/wheels/` 里除 `pydantic_core` 外都是纯 Python wheel，可跨平台安装；
`pydantic_core` 是编译好的二进制，当前锁定的是：

```
pydantic_core-2.41.5-cp312-cp312-macosx_11_0_arm64.whl
```

即 **Python 3.12 + macOS Apple Silicon (arm64)**。这套离线包只在这个组合上能免联网装上。
如果换到 Intel Mac、Linux 或别的 Python 小版本，`pip install --no-index` 那一步会报
`pydantic_core` 找不到匹配 wheel——此时必须联网重新 `pip download` 一次（见步骤 4 的替代命令）。

## 步骤

### 1. 确认 Python 版本

```bash
python3.12 --version
```

需要 3.11 及以上；本仓库用 3.12 锁定。如果没有 3.12，先装一个（`brew install python@3.12`
或官网安装包），这一步需要联网，仅此一次、仅这台新机器需要。

### 2. 建 venv

```bash
cd ai-test-loop-demo
python3.12 -m venv .venv
source .venv/bin/activate
```

### 3. 离线安装依赖（不联网）

```bash
pip install --no-index --find-links vendor/wheels -r requirements.lock.txt
```

### 4.（仅当步骤 3 报 wheel 不匹配时）联网重新生成离线包

```bash
pip install -r requirements.txt
pip freeze > requirements.lock.txt
rm -rf vendor/wheels && mkdir -p vendor/wheels
pip download -r requirements.lock.txt -d vendor/wheels --no-deps
```

### 5. 冒烟检查

```bash
python scripts/smoke_check.py
```

看到 `SMOKE STATUS: READY` 即可。这一步只查环境（Python 版本、依赖版本、app 能否起来、
离线包在不在），不跑业务测试逻辑。

### 6. 课前自检

```bash
python scripts/validate_demo.py
```

看到最后一行 `DEMO READY` 说明 Demo 处于可开课状态：服务可加载、订单接口存在、
GOLD+1000 可正常调用、文档规定正确值、课堂 Agent 工作区已清空。

### 7. 启动服务（可选，现场展示用）

```bash
uvicorn app.main:app --reload
```

访问 <http://127.0.0.1:8000/docs> 查看接口文档。课堂 Agent 也可用 FastAPI `TestClient`
直接跑测试，不依赖端口。

## 目录说明

- `requirements.txt` —— 人读的依赖范围声明。
- `requirements.lock.txt` —— 精确版本锁定，供离线安装与 `smoke_check.py` 校验。
- `vendor/wheels/` —— 离线 wheel 缓存，配合 lock 文件实现零 PyPI 访问安装。
- `docs/business-rules.md` —— 业务规则 Source of Truth。
- `agent_workspace/` —— 课堂 Agent 的私有工作区，`reset_demo.py` 只清理这里。
- `archive/old-demo/` —— 旧版「AI 测试闭环」Demo 存档，不属于当前课程。
