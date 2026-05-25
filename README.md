# 合同管理系统 V1（前后端分离，可本地直接跑）

这是一个适合你当前阶段的 **第一版可运行项目**：

- 前端：Vue 3 + Vite + Pinia + Vue Router + Element Plus
- 后端：Flask + Flask-SQLAlchemy + JWT
- 数据库：**默认 SQLite（方便本地先跑通）**，后续可切 PostgreSQL
- 功能：
  - 登录
  - 角色/权限基础模型
  - 合同基础信息增删改查
  - 财务记录：开票 / 收款 / 付款
  - 验收记录
  - 附件上传 / 下载
  - 审计日志（后端接口已提供）
  - 首页统计
  - 合同版本号（乐观锁基础）

> 说明：这一版的重点是 **先把业务骨架跑起来**，让你能马上开发和验收，而不是一开始就把审批流、消息通知、报表中心、多租户全部塞进去。

---

## 一、项目目录

```bash
contract-system-v1/
├── README.md
├── backend/
│   ├── .env.example
│   ├── requirements.txt
│   ├── run.py
│   └── app/
└── frontend/
    ├── package.json
    ├── vite.config.js
    └── src/
```

---

## 二、本地运行（推荐先这样跑）

下面步骤按顺序执行。

### 第 1 步：启动后端

进入后端目录：

```bash
cd backend
```

创建虚拟环境：

```bash
python -m venv .venv
```

激活虚拟环境：

#### Windows PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
```

#### Windows CMD

```bat
.venv\Scripts\activate
```

#### macOS / Linux

```bash
source .venv/bin/activate
```

安装依赖：

```bash
pip install -r requirements.txt
```

复制环境变量文件：

#### Windows

```bat
copy .env.example .env
```

#### macOS / Linux

```bash
cp .env.example .env
```

初始化数据库表：

```bash
flask --app run.py init-db
```

灌入测试数据：

```bash
flask --app run.py seed
```

启动后端：

```bash
flask --app run.py run
```

启动成功后，接口地址默认是：

```text
http://127.0.0.1:5000
```

健康检查：

打开浏览器访问：

```text
http://127.0.0.1:5000/api/health
```

如果看到：

```json
{"message":"ok"}
```

说明后端没问题。

---

### 第 2 步：启动前端

打开 **新的终端窗口**，进入前端目录：

```bash
cd frontend
```

安装依赖：

```bash
npm install
```

启动前端：

```bash
npm run dev
```

启动后，通常访问：

```text
http://127.0.0.1:5173
```

---

## 三、默认测试账号

后端 `seed` 命令会自动创建这些账号：


| 角色     | 用户名   | 密码        |
| -------- | -------- | ----------- |
| 管理员   | admin    | Admin123!   |
| 财务     | finance1 | Finance123! |
| 项目经理 | pm1      | Project123! |
| 销售     | sales1   | Sales123!   |

建议你先用：

```text
admin / Admin123!
```

---

## 四、你能先测试哪些功能

登录后，建议按这个顺序验证：

1. 进入首页看统计
2. 打开合同列表
3. 点“新建合同”
4. 填基础信息并保存
5. 进入详情页新增：
   - 开票记录
   - 收款记录
   - 付款记录
   - 验收记录
6. 上传一个附件
7. 下载附件
8. 删除合同

---

## 五、如果前端启动失败，优先检查这些问题

### 1. Node 版本太旧

Vue 官方当前本地搭建文档要求 Node.js 版本为 `^20.19.0` 或 `>=22.12.0`，新项目默认使用基于 Vite 的构建方式。([cn.vuejs.org](https://cn.vuejs.org/guide/quick-start?utm_source=chatgpt.com))

你可以先检查：

```bash
node -v
npm -v
```

### 2. 前端依赖没安装完整

重新执行：

```bash
npm install
```

### 3. 后端没启动

前端通过 Vite 代理把 `/api` 请求转给 Flask，所以后端必须先开。

---

## 六、如果后端启动失败，优先检查这些问题

### 1. 没激活虚拟环境

先确认命令行前面有 `(.venv)`。

### 2. 依赖没装

重新执行：

```bash
pip install -r requirements.txt
```

### 3. 启动命令不对

Flask 官方文档推荐通过 `flask --app ... run` 或 `python -m flask` 指定应用入口。([flask.palletsprojects.com](https://flask.palletsprojects.com/en/stable/quickstart/?utm_source=chatgpt.com))

所以你要用：

```bash
flask --app run.py run
```

而不是随便直接运行某个包文件。

---

## 七、把 SQLite 切换成 PostgreSQL

这一版为了让你更快跑起来，默认使用 SQLite。

正式上服务器时，建议你把 `.env` 里的：

```env
SQLALCHEMY_DATABASE_URI=sqlite:///contract_system.db
```

改成：

```env
SQLALCHEMY_DATABASE_URI=postgresql+psycopg2://contract_user:StrongPassword123!@127.0.0.1:5432/contract_db
```

然后重新执行：

```bash
flask --app run.py init-db
flask --app run.py seed
```

> 后续正式生产建议再接入 Alembic 做数据库迁移管理。Alembic 是 SQLAlchemy 官方体系的数据库迁移工具。([alembic.sqlalchemy.org](https://alembic.sqlalchemy.org/en/latest/?utm_source=chatgpt.com))

---

## 八、这一版已经考虑过的“商用基础能力”

### 已做

- 前后端分离
- 角色/权限基础模型
- 财务模块拆表
- 附件表独立
- 审计日志接口
- 合同版本号（防止并发覆盖的基础）
- 结构支持 PostgreSQL

### 还没做，但下一版建议加

- 审批流
- 导入导出 Excel
- 消息提醒 / 到期提醒
- 文件预览
- 附件病毒扫描
- Redis + Celery 异步任务
- Nginx + Gunicorn + PostgreSQL 生产部署
- Alembic 数据迁移
- 审计日志前端页面
- 更细的数据权限范围（本人 / 本部门 / 全部）

---

## 九、生产部署提醒

Flask 官方文档明确说明：开发服务器不适合生产环境，正式部署应该使用 Gunicorn 等 WSGI 服务器，并通常放在 Nginx 后面。([flask.palletsprojects.com](https://flask.palletsprojects.com/en/stable/deploying/?utm_source=chatgpt.com))

所以你现在本地运行用：

```bash
flask --app run.py run
```

正式服务器部署建议改成：

- Nginx
- Gunicorn
- Flask API
- PostgreSQL
- Redis
- Celery

---

## 十、开发建议

你现在最适合的推进顺序是：

1. 先把这版在本地跑起来
2. 根据你的真实合同表字段继续补字段
3. 把审批流加进去
4. 把导入导出加进去
5. 再切 PostgreSQL
6. 最后上服务器

---

## 十一、接口概览

### 登录

- `POST /api/auth/login`
- `GET /api/auth/me`

### 基础资料

- `GET /api/meta/users`
- `GET /api/meta/departments`
- `GET /api/meta/companies`
- `POST /api/meta/companies`

### 合同

- `GET /api/contracts`
- `POST /api/contracts`
- `GET /api/contracts/{id}`
- `PUT /api/contracts/{id}`
- `DELETE /api/contracts/{id}`
- `POST /api/contracts/{id}/status`

### 财务 / 验收

- `POST /api/contracts/{id}/invoices`
- `POST /api/contracts/{id}/receipts`
- `POST /api/contracts/{id}/payments`
- `POST /api/contracts/{id}/acceptances`

### 文件

- `POST /api/contracts/{id}/files`
- `GET /api/files/{id}/download`
- `DELETE /api/files/{id}`

### 统计 / 日志

- `GET /api/dashboard/summary`
- `GET /api/audit-logs`
