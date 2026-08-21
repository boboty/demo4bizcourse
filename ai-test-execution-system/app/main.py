from __future__ import annotations

import json
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.runtime import RuntimeStore


class LoginRequest(BaseModel):
    username: str


class ConfigRequest(BaseModel):
    ui_version: Optional[Literal["v1", "v2"]] = None
    payment_mode: Optional[Literal["normal", "timeout_before_commit", "timeout_after_commit"]] = None
    product_bug_mode: Optional[Literal["off", "on"]] = None


def create_app(store: Optional[RuntimeStore] = None) -> FastAPI:
    app = FastAPI(title="Round 0.5 本地 Mock 业务系统", version="0.5.0")
    app.state.store = store or RuntimeStore()

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/api/reset")
    def reset() -> dict:
        state = app.state.store.reset()
        return {"baseline": "restored", "order_id": state["orders"][0]["id"], "settings": state["settings"]}

    @app.post("/api/test-data/prepare-pending-order")
    def prepare_pending_order() -> dict:
        state = app.state.store.prepare_pending_order()
        return {
            "user_id": state["users"][0]["id"],
            "order_id": state["orders"][0]["id"],
            "order_status": state["orders"][0]["status"],
        }

    @app.post("/api/login")
    def login(request: LoginRequest) -> dict:
        user = app.state.store.login(request.username)
        if user is None:
            raise HTTPException(status_code=401, detail="测试用户不存在")
        return {"user": user}

    @app.get("/api/orders")
    def list_orders(user_id: str = Query(...), status: Optional[str] = Query(None)) -> dict:
        return {"orders": app.state.store.list_orders(user_id, status)}

    @app.get("/api/orders/{order_id}/facts")
    def order_facts(order_id: str) -> dict:
        facts = app.state.store.order_facts(order_id)
        if facts is None:
            raise HTTPException(status_code=404, detail="订单不存在")
        return facts

    @app.post("/api/orders/{order_id}/pay")
    def pay(order_id: str) -> dict:
        outcome, payment = app.state.store.pay(order_id)
        if outcome == "not_found":
            raise HTTPException(status_code=404, detail="订单不存在")
        if outcome == "already_paid":
            raise HTTPException(status_code=409, detail="订单已支付；请查询业务事实，不能重复付款")
        if outcome == "timeout_before_commit":
            raise HTTPException(status_code=504, detail="支付请求超时，业务未提交")
        if outcome == "timeout_after_commit":
            raise HTTPException(status_code=504, detail="支付请求超时；请先查询业务状态，不能直接重试")
        return {"payment": payment, "order_status": "PAID"}

    @app.get("/api/config")
    def get_config() -> dict:
        return app.state.store.get_settings()

    @app.put("/api/config")
    def set_config(request: ConfigRequest) -> dict:
        try:
            settings = app.state.store.configure(request.model_dump())
        except AttributeError:  # 兼容课程机器上可能存在的 Pydantic v1。
            settings = app.state.store.configure(request.dict())
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error))
        return settings

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def mobile_web() -> HTMLResponse:
        # UI V1/V2 是课堂中运行时切换的受控变量；Safari 不得复用旧页面缓存。
        return HTMLResponse(
            render_mobile_page(app.state.store.get_settings()["ui_version"]),
            headers={"Cache-Control": "no-store"},
        )

    return app


def render_mobile_page(ui_version: str) -> str:
    if ui_version == "v1":
        pay_button = '<button id="pay-now" data-testid="pay-button" type="button">立即支付</button>'
        pay_selector = json.dumps("#pay-now")
    else:
        pay_button = '<button data-testid="confirm-payment" type="button">确认支付</button>'
        pay_selector = json.dumps("[data-testid='confirm-payment']")

    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>课程支付演示</title>
  <style>
    :root { font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif; color: #172033; background: #f4f7fb; }
    body { margin: 0; padding: 24px 16px; } main { max-width: 430px; margin: auto; }
    .card { background: white; border-radius: 14px; box-shadow: 0 6px 22px #17203318; padding: 20px; margin: 14px 0; }
    h1 { font-size: 24px; margin: 8px 0; } h2 { font-size: 18px; } p { color: #536179; }
    input, button { box-sizing: border-box; width: 100%; padding: 12px; border-radius: 9px; font-size: 16px; }
    input { margin: 8px 0 12px; border: 1px solid #b9c5d8; } button { border: 0; background: #1769e0; color: white; font-weight: 650; }
    button + button { margin-top: 10px; } [hidden] { display: none; } .success { color: #147445; font-weight: 700; } .failure { color: #a02626; font-weight: 700; }
    .order { border: 1px solid #d6e0ef; background: #f8fbff; color: #172033; text-align: left; }
  </style>
</head>
<body>
  <main>
    <h1>课程支付演示</h1>
    <p>完全本地 Mock 业务，不连接真实支付。</p>
    <section class="card" data-testid="login-panel">
      <h2>登录</h2>
      <label for="username">测试账号</label>
      <input id="username" value="course-demo" autocomplete="username">
      <button data-testid="login-button" type="button" onclick="login()">登录</button>
      <p id="login-message" role="status"></p>
    </section>
    <section class="card" id="orders-panel" hidden>
      <h2>待付款订单</h2>
      <div id="orders"></div>
    </section>
    <section class="card" id="detail-panel" hidden>
      <h2>订单详情</h2>
      <p id="order-detail"></p>
      """ + pay_button + """
    </section>
    <section class="card" id="result-panel" hidden>
      <h2>支付结果</h2>
      <p data-testid="payment-result" id="payment-result" role="status"></p>
    </section>
  </main>
  <script>
    let currentUser = null;
    let currentOrderId = null;
    const setMessage = (id, text, klass = '') => { const node = document.getElementById(id); node.textContent = text; node.className = klass; };
    async function login() {
      const username = document.getElementById('username').value.trim();
      const response = await fetch('/api/login', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username})});
      if (!response.ok) { setMessage('login-message', '登录失败', 'failure'); return; }
      currentUser = (await response.json()).user;
      setMessage('login-message', '登录成功', 'success');
      const orders = await (await fetch('/api/orders?user_id=' + encodeURIComponent(currentUser.id) + '&status=PENDING_PAY')).json();
      const container = document.getElementById('orders');
      container.innerHTML = '';
      orders.orders.forEach(order => {
        const button = document.createElement('button');
        button.className = 'order'; button.dataset.testid = 'pending-order';
        button.textContent = '待付款订单 ' + order.id;
        button.onclick = () => openOrder(order); container.appendChild(button);
      });
      document.getElementById('orders-panel').hidden = false;
    }
    function openOrder(order) {
      currentOrderId = order.id;
      document.getElementById('order-detail').textContent = '订单 ' + order.id + '，状态：' + order.status;
      document.getElementById('detail-panel').hidden = false;
    }
    async function pay() {
      const response = await fetch('/api/orders/' + encodeURIComponent(currentOrderId) + '/pay', {method: 'POST'});
      document.getElementById('result-panel').hidden = false;
      if (response.ok) {
        setMessage('payment-result', '支付成功', 'success');
      } else {
        setMessage('payment-result', '支付请求失败；请先查询业务状态，不能直接重试。', 'failure');
      }
    }
    document.querySelector(""" + pay_selector + """).addEventListener('click', pay);
  </script>
</body>
</html>"""


app = create_app()
