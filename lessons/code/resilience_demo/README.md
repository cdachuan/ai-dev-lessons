# 真实世界数据 Agent 容错参考 Demo

P6 第41课配套代码 — 演示 Agent 面对真实世界脏接口/脏数据时的三种容错策略。

## 文件结构

```
resilience_demo/
├── http_retry.py    # 场景1: HTTP重试与降级
├── dirty_data.py    # 场景2: 脏数据护栏
├── schema_guard.py  # 场景3: Schema防护
└── README.md
```

## 三个场景与 Agent 工具层的对应关系

| 场景 | 文件 | 护栏类型 | Agent 中的位置 | 核心机制 |
|------|------|----------|---------------|----------|
| HTTP重试与降级 | `http_retry.py` | **执行护栏** | Agent 调用外部工具函数内部 | timeout + 指数退避 + 缓存降级 |
| 脏数据护栏 | `dirty_data.py` | **输入护栏** | Agent 收到数据后、分析前 | 检测→处理→留痕 |
| Schema防护 | `schema_guard.py` | **输入护栏** | Agent 解析工具返回值时 | 列名映射 + 类型断言 |

### 护栏分层说明

```
用户输入 → [输入护栏] → Agent推理 → [执行护栏] → 外部API/工具 → [输出护栏] → 返回用户
              ↑                          ↑                          ↑
         dirty_data.py             http_retry.py              schema_guard.py
         schema_guard.py
```

- **输入护栏**（dirty_data.py, schema_guard.py）：脏数据/异常结构在进入 Agent 推理循环之前就被拦截
- **执行护栏**（http_retry.py）：Agent 调用外部工具时的容错（重试、降级、超时）
- **输出护栏**（schema_guard.py）：工具返回结果的结构校验，确保 Agent 能安全解析

---

## 实跑记录

### Demo 1: HTTP重试与降级 (`http_retry.py`)

```
============================================================
Demo 1: HTTP重试与降级
============================================================
  [LOG] 第 1 次请求 → https://wttr.in/Beijing?format=j1
  [LOG] 成功！HTTP 200

[结果] 北京当前天气: 26°C, 湿度 52%, 风速 9 km/h
       描述: 未知

------------------------------------------------------------
演示：请求一个不存在的URL（模拟脏接口）
------------------------------------------------------------
  [LOG] 第 1 次请求 → https://wttr.in/INVALID_CITY_12345?format=j1&timeout=1
  [LOG] HTTP错误 500: 500 Server Error: Internal Server Error for url: https://wttr.in/INVALID_CITY_12345?format=j1&timeout=1
  [LOG] 等待 2s 后重试...
  [LOG] 第 2 次请求 → https://wttr.in/INVALID_CITY_12345?format=j1&timeout=1
  [LOG] HTTP错误 500: 500 Server Error: Internal Server Error for url: https://wttr.in/INVALID_CITY_12345?format=j1&timeout=1
  [LOG] 等待 4s 后重试...
  [LOG] 第 3 次请求 → https://wttr.in/INVALID_CITY_12345?format=j1&timeout=1
  [LOG] HTTP错误 500: 500 Server Error: Internal Server Error for url: https://wttr.in/INVALID_CITY_12345?format=j1&timeout=1
  [LOG] 等待 8s 后重试...
  [LOG] 重试 3 次均失败，进入降级逻辑
  [LOG] 无缓存可用，返回 None

[结果] 降级返回: <class 'NoneType'>
```

**要点：**
- 正常请求 200 OK，直接返回天气数据
- 脏接口返回 500，指数退避重试（2s → 4s → 8s）
- 3次全部失败后优雅降级返回 None

### Demo 2: 脏数据护栏 (`dirty_data.py`)

```
============================================================
Demo 2: 脏数据护栏
============================================================
  [LOG] 读取 online_retail_2010_2011.csv 前 10000 行...
  [LOG] 原始行数: 10000
  [LOG] [缺失值- CustomerID] 检测到 2291 行问题
  [LOG] [缺失值- CustomerID] 处理: 丢弃 2291 行 → 剩余 7709 行
  [LOG] [负数退货] 检测到 100 行问题
  [LOG] [负数退货] 处理: 丢弃 100 行 → 剩余 7609 行
  [LOG] [异常单价] 检测到 1 行问题
  [LOG] [异常单价] 处理: 丢弃 1 行 → 剩余 7608 行
  [LOG] [重复发票行] 检测到 196 行问题
  [LOG] [重复发票行] 处理: 丢弃 196 行 → 剩余 7412 行

--- 清洗统计 ---
  缺失值(CustomerID): 2291
  负数退货: 100
  异常单价(<=0或>5000): 1
  重复行: 196
  清洗前行数: 10000
  清洗后行数: 7412
  总丢弃行数: 2588

--- 退货行样本（前5行）---
InvoiceNo                      Description  Quantity  UnitPrice
  C536379                         Discount        -1      27.50
  C536383  SET OF 3 COLOURED  FLYING DUCKS        -1       4.65
  C536391   PLASTERS IN TIN CIRCUS PARADE        -12       1.65
  C536391 PACK OF 12 PINK PAISLEY TISSUES        -24       0.29
  C536391 PACK OF 12 BLUE PAISLEY TISSUES        -24       0.29

--- 清洗后数据画像 ---
  行数: 7412
  列数: 9
  UnitPrice 范围: 0.10 ~ 295.00
  Quantity 范围: 1 ~ 2880
  唯一客户数: 303

--- 清洗后前3行 ---
InvoiceNo                        Description  Quantity  UnitPrice  CustomerID
   536365 WHITE HANGING HEART T-LIGHT HOLDER         6       2.55     17850.0
   536365                WHITE METAL LANTERN         6       3.39     17850.0
   536365     CREAM CUPID HEARTS COAT HANGER         8       2.75     17850.0
```

**四类脏数据处理结果：**

| 类型 | 检测行数 | 处理方式 |
|------|---------|---------|
| 缺失值 (CustomerID) | 2291 | 丢弃 |
| 负数退货 | 100 | 丢弃 |
| 异常单价 (<=0 或 >5000) | 1 | 丢弃 |
| 重复行 | 196 | 丢弃 |

**清洗率：** 10000 → 7412 行（丢弃 2588 行，25.9%）

### Demo 3: Schema防护 (`schema_guard.py`)

```
============================================================
Demo 3: Schema防护
============================================================

--- Case 1: 正常数据（标准列名）---
  [LOG] 列名映射完成: ['InvoiceNo', 'StockCode', ...] → ['InvoiceNo', 'StockCode', ...]
  [LOG] 必需字段检查通过: ['InvoiceNo', 'Quantity', 'UnitPrice', 'CustomerID']
  [LOG] 类型断言通过
  [OK] {'InvoiceNo': '536365', 'StockCode': '85123A', ...}

--- Case 2: 列名变了（别名兼容）---
  [LOG] 列名映射完成: ['order_id', 'product_code', 'item_name', 'qty', ...] → ['InvoiceNo', 'StockCode', ...]
  [LOG] 必需字段检查通过: ['InvoiceNo', 'Quantity', 'UnitPrice', 'CustomerID']
  [LOG] 类型断言通过
  [OK] {'InvoiceNo': '536366', 'StockCode': '22633', ...}

--- Case 3: 缺少字段（CustomerID缺失）---
  [清晰错误] "缺少必需字段: ['CustomerID']。可用字段: [InvoiceNo, Quantity, UnitPrice]"

--- Case 4: 类型变化（InvoiceNo变成数字）---
  [清晰错误] 类型校验失败:
  字段 'InvoiceNo' 期望 str，实际是 int（值=536368）
  字段 'Quantity' 期望 int | float，实际是 str（值='七'）
  字段 'UnitPrice' 期望 int | float，实际是 str（值='free'）

--- Case 5: 完全陌生的列名（无法映射）---
  [清晰错误] "缺少必需字段: ['InvoiceNo', 'Quantity', 'UnitPrice', 'CustomerID']。可用字段: []"
```

**要点：**
- Case 2 展示别名兼容：`order_id` → `InvoiceNo`，`qty` → `Quantity`，无需改调用方代码
- Case 3-5 的错误信息清晰告知"缺什么"和"有什么"，不是深层 stack trace

---

## 运行方式

```bash
# 在 resilience_demo/ 目录下
python http_retry.py
python dirty_data.py
python schema_guard.py
```

## 依赖

- Python 3.11+
- requests
- pandas
- 无其他第三方依赖，无需 API Key

## 与 insight_agent_mvp 的关系

本 demo 的 `dirty_data.py` 中的清洗逻辑，对应 `insight_agent_mvp/agent/tools.py` 中 `_load_data()` 的同类处理（缺失值、退货、异常单价）。本 demo 将这些逻辑拆解为独立的"检测→处理→留痕"三步，更适合作为教学演示。
