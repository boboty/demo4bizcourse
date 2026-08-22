# Round 0.5 PASS 摘要（脱敏）

- FastAPI：PASS（本机启动并完成 HTTP 验收）
- Mac 浏览器：PASS（登录 → 待付款订单 → 支付 → 支付成功）
- iPhone Safari：PASS（人工完成同一流程）
- 测试数据：PASS（固定 `PENDING_PAY` 订单）
- normal：PASS（`PAID`、Payment=1、库存从 10 变为 9）
- timeout_before_commit：PASS（HTTP 504、订单仍为 `PENDING_PAY`、Payment=0、库存=10）
- timeout_after_commit：PASS（HTTP 504、订单为 `PAID`、Payment=1、库存=9）
- PRODUCT_BUG_MODE=on：PASS（付款成功但库存保持 10，故障可确定性复现）
- UI V1/V2：PASS（V1 有 `#pay-now`；V2 不存在该元素，且有 `data-testid="confirm-payment"`）
- reset：PASS（连续两次恢复相同 baseline：V1、normal、产品故障关闭、`PENDING_PAY`、库存=10、Payment=0）

本摘要不包含设备标识、账号标识、绝对路径、原始日志或截图。
