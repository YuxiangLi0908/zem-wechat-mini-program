# Zem WeChat Mini Program 后端服务

微信小程序后端 API 服务，提供用户登录和柜号查询功能。

## 功能概述

### 1. 用户登录接口
- **路径**: `POST /login`
- **功能**: 用户登录验证，支持客户和员工两类用户
- **登录验证顺序**:
  1. 优先查询 `warehouse_customer` 表（客户用户）
  2. 若不存在，查询 `auth_user` 表（员工用户）

### 2. 柜号查询接口
- **路径**: `POST /order_tracking`
- **功能**: 查询柜号的完整物流追踪信息
- **权限控制**:
  - 客户用户：只能查看归属于自己的柜号
  - 员工用户：可查看所有柜号

---

## 接口调用示例

### 登录接口

**请求**:
```http
POST /login
Content-Type: application/json

{
    "username": "your_username",
    "password": "your_password"
}
```

**成功响应** (客户用户):
```json
{
    "user": "客户显示名称",
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "user_type": "customer"
}
```

**成功响应** (员工用户):
```json
{
    "user": "员工姓名",
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "user_type": "staff"
}
```

**错误响应**:
```json
// 用户不存在 (404)
{"detail": "User not found / 用户不存在"}

// 密码错误 (401)
{"detail": "Invalid credentials / 密码错误"}

// 账户禁用 (401)
{"detail": "Account is disabled / 账户已禁用"}
```

---

### 柜号查询接口

**请求**:
```http
POST /order_tracking
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
Content-Type: application/json

{
    "container_number": "ABCD1234567"
}
```

**成功响应** (有权限):
```json
{
    "preport_timenode": {
        "order_id": "ORD-20260115-001",
        "created_at": "2026-01-15T10:30:00",
        "eta": "2026-02-01",
        "container": {"container_number": "ABCD1234567", "container_type": "40HQ"},
        "history": [
            {"status": "ORDER_CREATED", "description": "创建订单: ABCD1234567"},
            {"status": "ARRIVED_AT_PORT", "description": "到达港口: 洛杉矶"},
            {"status": "OFFLOAD", "description": "拆柜完成"}
        ]
    },
    "postport_timenode": {
        "shipment": [
            {"destination": "Amazon FBA", "is_shipped": true, "is_arrived": true}
        ]
    },
    "has_permission": true,
    "message": null
}
```

**响应** (客户无权限查看此柜号):
```json
{
    "preport_timenode": null,
    "postport_timenode": null,
    "has_permission": false,
    "message": "您没有权限查看柜号 ABCD1234567 的详情，该柜子归属于其他客户"
}
```

**响应** (柜号不存在):
```json
{
    "preport_timenode": null,
    "postport_timenode": null,
    "has_permission": true,
    "message": "未找到柜号 ABCD1234567 的相关信息"
}
```

---

## 环境配置

### 必需环境变量

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `ENV` | 运行环境 | `local` / `production` |
| `JWT_SECRET_KEY` | JWT 签名密钥（必须与 zem-client-svc 一致） | `your-secret-key` |

### 生产环境数据库配置

| 变量名 | 说明 |
|--------|------|
| `DBUSER` | 数据库用户名 |
| `DBPASS` | 数据库密码 |
| `DBHOST` | 数据库主机 |
| `DBPORT` | 数据库端口 |
| `DBNAME` | 数据库名称 |

### 本地开发环境

| 变量名 | 说明 |
|--------|------|
| `POSTGRESQL_PWD` | 本地 PostgreSQL 密码 |

---

## 项目结构

```
zem-wechat-mini-program/
├── app/
│   ├── main.py                    # FastAPI 应用入口
│   ├── api/
│   │   ├── router.py              # API 路由配置
│   │   ├── heartbeat.py           # 健康检查接口
│   │   ├── login.py               # 登录接口
│   │   └── order_tracking.py      # 柜号查询接口
│   ├── data_models/
│   │   ├── heartbeat.py           # 健康检查数据模型
│   │   ├── login.py               # 登录相关数据模型
│   │   ├── order_tracking.py      # 查询相关数据模型
│   │   └── db/                    # 数据库 ORM 模型
│   └── services/
│       ├── config.py              # 应用配置
│       ├── db_session.py          # 数据库会话管理
│       ├── user_auth.py           # 用户认证服务
│       └── order_history.py       # 订单追踪服务
├── pyproject.toml
├── Dockerfile
└── README.md
```

---

## 关键业务规则

### 1. 登录验证顺序

```
用户提交 username + password
    │
    ▼
查询 warehouse_customer 表
    │
    ├── 找到 → 验证密码 → 成功 → 返回 user_type="customer"
    │
    └── 未找到 → 查询 auth_user 表
                    │
                    ├── 找到 → 验证密码 → 成功 → 返回 user_type="staff"
                    │
                    └── 未找到 → 返回 404 用户不存在
```

### 2. 柜号查询权限验证

```
用户请求查询柜号
    │
    ▼
解析 JWT Token 获取用户信息
    │
    ├── user_type = "staff" (员工)
    │       └── 直接返回完整柜号信息（无需验证归属）
    │
    └── user_type = "customer" (客户)
            │
            ▼
        查询订单，获取 customer_name_id
            │
            ├── 匹配当前用户 → 返回完整柜号信息
            │
            └── 不匹配 → 返回 has_permission=false
```

### 3. 与 zem-client-svc 的对齐点

| 功能点 | 对齐说明 |
|--------|----------|
| 数据库连接 | 连接同一数据库，使用相同的环境变量 |
| 密码验证 | 使用 Django PBKDF2-SHA256 算法 |
| JWT 配置 | 使用相同的 SECRET_KEY 和 HS256 算法 |
| 数据模型 | ORM 模型与 zem-client-svc 完全一致 |
| 查询逻辑 | 港前港后轨迹构建逻辑与 zem-client-svc 一致 |

---

## 运行服务

```bash
# 安装依赖
pip install -e .

# 本地开发运行
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产环境运行
ENV=production uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 微信小程序前端对接

### 登录流程

```javascript
wx.request({
  url: 'https://your-api-domain.com/login',
  method: 'POST',
  data: { username: 'your_username', password: 'your_password' },
  success: (res) => {
    wx.setStorageSync('access_token', res.data.access_token);
    wx.setStorageSync('user_type', res.data.user_type);
  }
});
```

### 查询柜号

```javascript
const token = wx.getStorageSync('access_token');
wx.request({
  url: 'https://your-api-domain.com/order_tracking',
  method: 'POST',
  header: { 'Authorization': `Bearer ${token}` },
  data: { container_number: 'ABCD1234567' },
  success: (res) => {
    if (res.data.has_permission) {
      // 展示柜号信息
    } else {
      wx.showToast({ title: res.data.message, icon: 'none' });
    }
  }
});
```

---

## 注意事项

1. **JWT 密钥一致性**: `JWT_SECRET_KEY` 必须与 zem-client-svc 保持一致
2. **数据库连接**: 使用与 zem-client-svc 相同的数据库配置
3. **HTTPS 要求**: 微信小程序要求后端接口必须使用 HTTPS
4. **域名配置**: 需要在微信小程序后台配置合法的请求域名