# Demo 3｜独立验收上下文

本目录只包含业务事实源（放款处理导出规则、tenant 权限、已知融资申请记录）、Golden Case 输入、独立验收指令和黑盒输出入口。它没有被验收系统的实现代码和开发侧测试。

```bash
../../.venv/bin/python -m pytest -q
../../.venv/bin/python bin/actual-output validation/cases.json
```

先按 `validation/independent-validation.md` 形成 Independent Expectation，再运行黑盒入口（默认访问 `http://127.0.0.1:8030`，即开发方 `demo3_serve.sh` 起的服务）取得实际输出；不要把被验收工程源码复制到本目录。
