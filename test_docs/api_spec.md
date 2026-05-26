# Payment Gateway API v2.3 接口文档

## 1. 概述

Payment Gateway（支付网关）是电商平台核心交易系统的统一支付入口。当前版本 v2.3，支持微信支付、支付宝、银联云闪付三种支付渠道。

## 2. 接口列表

### 2.1 创建订单
```
POST /api/v2/order/create
```
创建支付订单。必传参数：
- `merchant_id`：商户号
- `amount`：订单金额（单位：分）
- `channel`：支付渠道（WECHAT / ALIPAY / UNIONPAY）
- `notify_url`：异步回调地址

### 2.2 查询订单
```
POST /api/v2/order/query
```
根据 `order_id` 或 `merchant_order_no` 查询订单状态。

### 2.3 发起退款
```
POST /api/v2/refund/create
```
创建退款单。注意：部分退款金额不得大于原订单金额。

### 2.4 查询退款
```
POST /api/v2/refund/query
```
根据 `refund_id` 或 `order_id` 查询退款状态。

## 3. 签名算法

所有请求需附带 `sign` 字段。签名步骤：
1. 将请求参数按 key 字典序排序
2. 拼接为 `key1=value1&key2=value2` 格式
3. 末尾追加 `&key=MERCHANT_SECRET`（商户密钥）
4. 计算 MD5 哈希值，转大写

## 4. 错误码

| 错误码 | 含义 |
|--------|------|
| 1001 | 参数缺失 |
| 1002 | 签名验证失败 |
| 2001 | 商户不存在 |
| 2002 | 商户余额不足 |
| 3001 | 订单不存在 |
| 3002 | 订单已关闭 |
| 4001 | 退款金额超限 |

## 5. 注意事项

- 同一订单号不可重复创建订单
- 退款接口仅支持原订单创建后 90 天内的交易
- 测试环境商户密钥统一为 `TEST_SECRET_KEY_2025`
