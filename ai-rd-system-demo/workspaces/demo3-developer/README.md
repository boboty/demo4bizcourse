# Demo 3｜开发上下文

这是融资申请功能的历史开发状态：客户名称筛选、融资状态筛选、导出三项功能都已经做完，实现与开发侧测试保持同一理解，开发测试全绿，`./bin/self-check` 结论是 PASS。独立验收角色使用另一个 workspace（`../demo3-validator`），本目录不放置独立验收脚本、Golden Case 或业务事实源。

```bash
../../.venv/bin/python -m pytest -q
./verify.sh
./bin/self-check
```

浏览器查看（另起终端，保持运行）：

```bash
../../.venv/bin/python -m uvicorn app.main:app --reload --port 8030
```

打开 http://127.0.0.1:8030/ ，客户名称筛选、融资状态筛选、导出三项都能实际点用。
