# 环境搭建（现场演示用）

目标：换一台机器，5 分钟内跑到 `SMOKE STATUS: READY`。演示当天不需要联网。

## 已知限制（先看这个）

`vendor/wheels/` 里除 `pydantic_core` 外都是纯 Python wheel，可跨平台安装；`pydantic_core` 是编译好的二进制，当前锁定的是：

```
pydantic_core-2.41.5-cp312-cp312-macosx_11_0_arm64.whl
```

即 **Python 3.12 + macOS Apple Silicon (arm64)**。这套离线包只在这个组合上能免联网装上。如果换到 Intel Mac、Linux 或别的 Python 小版本，`pip install --no-index` 那一步会报 `pydantic_core` 找不到匹配 wheel——此时必须联网重新 `pip download` 一次（见下方步骤 4 的替代命令），别的都不用变。

## 步骤

### 1. 确认 Python 版本

```bash
python3.12 --version
```

需要 3.11 及以上；本仓库用 3.12 锁定。如果没有 3.12，去装一个（`brew install python@3.12` 或官网安装包），**这一步需要联网**，仅此一次、仅这台新机器需要。

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

`--no-index` 强制 pip 不去访问 PyPI，只用 `vendor/wheels/` 里的文件；装不上就是上面"已知限制"命中了。

### 4.（仅当步骤3报 wheel 不匹配时）联网重新生成离线包

```bash
pip install -r requirements.txt
pip freeze > requirements.lock.txt
rm -rf vendor/wheels && mkdir -p vendor/wheels
pip download -r requirements.lock.txt -d vendor/wheels --no-deps
```

跑完之后 `vendor/wheels/` 就适配新机器了，之后同一台机器可以一直离线用。

### 5. 冒烟检查

```bash
python scripts/smoke_check.py
```

看到 `SMOKE STATUS: READY` 即可。这一步只查环境（Python 版本、依赖版本、app 能不能起来、离线包在不在），不跑业务测试逻辑。

### 6.（可选）完整业务闭环验收

```bash
python scripts/validate_demo.py
```

看到 `DEMO STATUS: READY` 说明 generated/verified 两套测试和独立验收全链路可重跑。这一步比 `smoke_check.py` 慢一点（约1秒），演示前只需跑一次确认，不用每次都跑。

## 目录说明

- `requirements.txt` —— 人读的依赖范围声明（原有文件，不变）。
- `requirements.lock.txt` —— `pip freeze` 产出的精确版本锁定（含间接依赖），供离线安装与 `smoke_check.py` 校验用。
- `vendor/wheels/` —— 离线 wheel 缓存，已提交进仓库，配合 `requirements.lock.txt` 实现零 PyPI 访问安装。
- `.venv/` —— 本地虚拟环境，不提交（见 `.gitignore`），每台机器自己建。
