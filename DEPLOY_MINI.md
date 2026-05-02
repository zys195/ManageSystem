=# 合同管理系统 — 小型团队生产部署指南

> 适用规模：**5,000 合同 / 7 人同时在线**（内部小团队使用）

---

## 一、需求分析与服务器推荐

### 资源估算

| 项目 | 评估值 |
|------|--------|
| 合同数量 | ~5,000 条 |
| 数据库大小 | **200 - 400 MB** |
| 附件文件 | 5,000 个 × 平均 3MB ≈ **15 GB** |
| 同时在线人数 | **7 人** |
| 并发请求数 | 峰值 **20-40 QPS** |

### 推荐配置：2 核 4 GB（轻量应用服务器）

| 项目 | 配置 |
|------|------|
| CPU | **2 核** |
| 内存 | **4 GB** |
| 系统盘 | **50 - 80 GB SSD**（系统 + 应用） |
| 带宽 | **4 Mbps** |
| 操作系统 | **Ubuntu 22.04 LTS / Docker 22.04** |
| 参考价格 | **约 50 - 90 元/月** |

> 7 人同时在线对服务器压力极小，**2 核 4GB 绰绰有余**。

---

### 云平台购买推荐

#### 首选：腾讯云 Lighthouse（最推荐，性价比最高）

1. 打开 https://cloud.tencent.com/product/lighthouse
2. 选择「轻量应用服务器」
3. 地域：选择离你最近的区域（如广州/上海/北京）
4. 镜像：选 **Docker 22.04** 或 **Ubuntu 22.04 LTS**
5. 配置：
   - **CPU**: 2 核
   - **内存**: 4 GB
   - **SSD**: 60 GB
   - **带宽**: 4 Mbps 或 6 Mbps
6. 新用户优惠价通常在 **36-58 元/月**（首年）

> Lighthouse 自带简单防火墙管理面板，操作非常方便。

#### 备选：阿里云轻量应用服务器

1. 打开 https://swas.console.aliyun.com/
2. 配置：2核4G / 60GB SSD / 5Mbps
3. 镜像：Ubuntu 22.04 LTS
4. 参考：约 **50-70 元/月**

#### 备选：华为云耀云服务器

1. 打开 https://www.huaweicloud.com/product/lighthouse.html
2. 配置类似
3. 参考：约 **45-65 元/月**

### 购买后必做

1. 登录云平台控制台 → 找到「防火墙」或「安全组」
2. 添加以下放行规则：

| 端口 | 协议 | 说明 |
|------|------|------|
| 22 | TCP | SSH 远程连接 |
| 80 | TCP | HTTP 访问前端页面 |
| 443 | TCP | HTTPS（可选，后续加 SSL 时需要） |

3. 用终端连接到服务器：
   ```
   ssh root@你的服务器公网IP
   ```

---

## 二、服务器环境准备

以下命令全部在**服务器上**以 root 用户执行（复制粘贴即可）。

### 第 1 步：基础更新

```bash
apt update && apt upgrade -y
```

### 第 2 步：安装 Docker 和 Docker Compose

```bash
# 安装依赖
apt install -y curl gnupg lsb-release

# 添加 Docker 官方 GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# 添加 Docker 官方源
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list

# 安装 Docker Engine + Compose 插件
apt update && apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 启动 Docker 并设置开机自启
systemctl enable --now docker
```

### 第 3 步：验证安装

```bash
docker --version           # 期望: Docker version 24.x+
docker compose version     # 期望: Docker Compose v2.x+

docker run hello-world      # 测试容器是否正常运行（成功后会自动删除）
```

如果 `hello-world` 输出 "Hello from Docker!" 则说明一切正常。

---

## 三、上传项目代码到服务器

### 方式 A：通过 Git 克隆（推荐，后续更新方便）

```bash
# 安装 git
apt install -y git

# 创建项目目录并进入
mkdir -p /opt && cd /opt

# 克隆你的代码仓库（替换为实际地址）
git clone https://github.com/你的用户名/FileManage.git contract-system

cd /opt/contract-system
```

### 方式 B：SFTP 上传（适合没有 Git 仓库的情况）

用以下任一工具连接服务器：
- **WinSCP**（Windows 推荐）
- **FileZilla**
- **FinalShell**
- **Termius**（带文件传输功能）

上传步骤：
1. 连接到服务器的 `/opt/` 目录
2. 将本地整个 `FileManage` 项目文件夹上传上去
3. 重命名为 `contract-system`
4. **确保 `.env`、`Dockerfile`、`nginx.conf` 等隐藏/配置文件都传上去了**

---

## 四、生产环境配置（关键步骤！）

```bash
cd /opt/contract-system
```

### 第 1 步：创建生产环境变量

```bash
cat > .env << 'EOF'
# ===== 合同管理系统 — 生产环境 =====
# 安全密钥（务必修改！）
SECRET_KEY=50debe1166a8aad8529d9bed7d158d5f1375cdcd31d124e9eda8459d1ea4be82
JWT_SECRET_KEY=184d8bc8ee86b9b2cb8221aa7c8782083384a8f469cb4090c8403ceaf029c531

# PostgreSQL 内部密码
DB_PASSWORD=ContractProd2026Secure!

# CORS 允许的来源（改为你的实际 IP 或域名）
CORS_ORIGINS=http://1.13.174.17

# Flask 运行配置
FLASK_DEBUG=false
FLASK_HOST=0.0.0.0
FLASK_PORT=5000

# 协作编辑（7人够用）
COLLAB_EDIT_LOCK_TIMEOUT=300
COLLAB_HEARTBEAT_INTERVAL=15
COLLAB_MAX_ONLINE_USERS=30
EOF
```

**生成安全密钥**（复制执行）：
```bash
python3 -c "
import secrets
print('=== 复制以下两行替换 .env 中对应的值 ===')
print('SECRET_KEY=' + secrets.token_hex(32))
print('JWT_SECRET_KEY=' + secrets.token_hex(32))
"
```

把输出结果替换 `.env` 中的 `请替换为随机密钥A` 和 `请替换为随机密钥B`。

### 第 2 步：同步后端 .env

后端 config.py 会读取 `backend/.env`，确保它存在且一致：

```bash
cp .env backend/.env
```

### 第 3 步：调整 Gunicorn 工作进程数（小团队优化）

7 人同时在线不需要太多 worker 进程，改为 2 个即可节省内存：

```bash
# 编辑 docker-compose.yml 中的 workers 数量
sed -i 's/GUNICORN_WORKERS.*"4"/GUNICORN_WORKERS":"2"/' docker-compose.yml
sed -i 's/"--threads", "50"/"--threads", "20"/' backend/Dockerfile
```

或者手动修改 `backend/Dockerfile` 第 33-36 行，将：
```
-w 4 --threads 50
```
改为：
```
-w 2 --threads 20
```

---

## 五、构建和启动服务

### 第 1 步：构建所有镜像（首次约 5-8 分钟）

```bash
cd /opt/contract-system
docker compose build
```

构建过程会下载基础镜像（Node.js、Python、Nginx、PostgreSQL），首次较慢，之后有缓存会很快。

### 第 2 步：启动全部服务

```bash
# 后台启动所有容器
docker compose up -d

# 查看运行状态
docker compose ps
```

期望看到三个容器都是 **running (healthy)**：

```
NAME                        STATUS              PORTS
contract_system-db-1        running (healthy)    5432/tcp
contract_system-backend-1   running             0.0.0.0:5000->5000/tcp
contract_system-frontend-1  running             0.0.0.0:80->80/tcp
```

> 如果 db 显示 `starting` 或 `unhealthy`，等待 10-15 秒再查看，PostgreSQL 首次初始化需要一点时间。

### 第 3 步：初始化数据库

```bash
# 创建所有数据表
docker compose exec backend flask --app run.py init-db

# 灌入测试账号数据（admin / Admin123! 等）
docker compose exec backend flask --app run.py seed
```

成功后会看到输出：
```
✅ 所有表创建完成！
📋 已创建 X 张表: ...
✅ 种子数据初始化完成！
管理员账号：admin / Admin123!
...
```

### 第 4 步：验证是否正常

```bash
# 测试健康检查接口
curl http://127.0.0.1/api/health

# 期望返回: {"message":"ok"}
```

然后在浏览器打开：**`http://你的服务器IP`**

默认登录账号：
| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | Admin123! |

---

## 六、域名绑定与 HTTPS（可选但强烈推荐）

### 第 1 步：购买域名并解析

1. 在域名服务商购买域名（腾讯云/阿里云/Cloudflare），例如 `ht.yourcompany.com`
2. 添加 A 记录解析：

| 主机记录 | 类型 | 记录值 | TTL |
|---------|------|--------|-----|
| @ | A | 你的服务器IP | 600 |
| www | A | 你的服务器IP | 600 |

### 第 2 步：申请免费 SSL 证书

```bash
# 安装 certbot（Let's Encrypt 免费证书工具）
apt install -y certbot python3-certbot-nginx

# 申请证书（替换成你的实际域名）
certbot --nginx -d ht.yourcompany.com -d www.ht.yourcompany.com
```

按提示操作：
- 选择邮箱接收通知
- 选择是否重定向 HTTP→HTTPS → **建议选 2（Redirect，自动跳转 HTTPS）**

certbot 会自动完成：
- ✅ 下载并安装 SSL 证书
- ✅ 自动修改 Nginx 配置启用 HTTPS
- ✅ 设置证书自动续期任务（每天检查一次，到期前自动续期）

### 第 3 步：验证

浏览器访问 **`https://ht.yourcompany.com`**，确认地址栏显示锁头图标 🔒。

---

## 七、日常运维速查手册

### 常用命令

```bash
cd /opt/contract-system

# === 查看日志 ===
docker compose logs -f                    # 全部服务实时日志
docker compose logs -f backend            # 仅后端日志
docker compose logs -f frontend           # 仅前端 Nginx 日志

# === 服务管理 ===
docker compose restart backend            # 重启后端（不改数据）
docker compose restart frontend           # 重启前端
docker compose down && docker compose up -d # 全部重启

# === 更新部署（代码更新后）===
git pull
docker compose build && docker compose up -d

# === 数据库备份 ===
docker compose exec -T db pg_dump -U contract_user contract_system > backup_$(date +%Y%m%d).sql
ls -lh backup_*.sql                       # 查看备份文件大小

# === 数据库恢复（谨慎操作！）===
cat backup_20260422.sql | docker compose exec -T db psql -U contract_user contract_system

# === 查看资源占用 ===
docker stats --no-stream                  # 各容器 CPU/内存使用情况
df -h                                      # 磁盘空间
du -sh backend/uploads/                   # 附件占用空间

# === 进入容器内部排查 ===
docker compose exec backend bash          # 进入后端容器
docker compose exec db psql -U contract_user -d contract_system  # 直接连数据库
```

### 设置每日自动备份

```bash
# 创建备份脚本
mkdir -p /opt/scripts

cat > /opt/scripts/backup.sh << 'SCRIPT'
#!/bin/bash
BACKUP_DIR="/opt/backups"
mkdir -p $BACKUP_DIR
DATE=$(date +%Y%m%d_%H%M%S)

# 备份数据库
cd /opt/contract-system
docker compose exec -T db pg_dump -U contract_user contract_system > "$BACKUP_DIR/db_$DATE.sql"

# 备份附件目录
tar czf "$BACKUP_DIR/files_$DATE.tar.gz" -C /opt/contract-system backend/uploads/

# 清理 14 天前的旧备份
find $BACKUP_DIR -name "*.sql" -mtime +14 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +14 -delete

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 备份完成"
SCRIPT

chmod +x /opt/scripts/backup.sh

# 设置每天凌晨 3 点自动执行
(crontab -l 2>/dev/null; echo "0 3 * * * /opt/scripts/backup.sh >> /var/log/backup.log 2>&1") | crontab -

echo "✅ 自动备份已设置：每天凌晨 3 点执行"
```

### 监控指标参考值（2核4GB 机器）

| 指标 | 正常范围 | 需要关注 | 危险阈值 |
|------|---------|---------|---------|
| CPU 使用率 | < 30% | > 60% | > 85% |
| 内存使用率 | < 55% | > 75% | > 90% |
| 磁盘使用率 | < 50% | > 70% | > 85% |
| 数据库活跃连接 | < 10 | > 25 | > 50 |

快速查看命令：
```bash
free -h                                    # 内存
nproc && cat /proc/cpuinfo | grep "model name" | head -1  # CPU
df -h /                                   # 磁盘
docker compose exec db psql -U contract_user -d contract_system -c "SELECT count(*) FROM pg_stat_activity;"  # 数据库连接数
```

---

## 八、故障排查速查表

| 现象 | 最可能原因 | 解决方法 |
|------|-----------|---------|
| 浏览器无法打开页面 | 前端容器没启动 | `docker compose ps` 查状态；`docker compose restart frontend` |
| 页面显示 502 Bad Gateway | 后端没启动或崩了 | `docker compose logs backend` 查错误日志；重启后端 |
| 登录报 500 错误 | 数据库未初始化 | `docker compose exec backend flask --app run.py init-db` |
| 上传附件失败 | uploads 目录权限不够 | `chmod 777 backend/uploads` |
| WebSocket 连接断开 | Nginx 超时设置太短 | 检查 `frontend/nginx.conf` 的 `proxy_read_timeout` 是否 >= 120s |
| 数据库连接被拒绝 | PostgreSQL 还没启动好 | `docker compose restart db` 等 15 秒后再 `restart backend` |
| 磁盘满了 | 附件积累太多 | `du -sh backend/uploads/*` 查大文件，清理无用附件 |
| 更新代码后不生效 | 镜像没有重新构建 | `docker compose build --no-cache && docker compose up -d` |

### 查看详细错误日志

```bash
# 后端 Python 报错详情（最常用）
docker compose logs backend --tail 100

# Nginx 错误日志
docker compose logs frontend --tail 50

# PostgreSQL 日志
docker compose logs db --tail 30
```

---

## 九、架构图

```
┌──────────────────────────────────────┐
│         用户浏览器 (7人)               │
│   https://你的域名                     │
└───────────────┬──────────────────────┘
                │ :443 (HTTPS) / :80 (HTTP)
┌───────────────▼──────────────────────┐
│        Nginx (Alpine)                 │
│  ┌──────────┬──────────────────────┐ │
│  │ 静态文件  │  反向代理 (/api/*)     │ │
│  │ Vue SPA  │  WebSocket(/socket.io)│ │
│  └──────────┴──────────────────────┘ │
└──────┬──────────────┬────────────────┘
       │ /api/*       │ /socket.io*
┌──────▼──────────────▼────────────────┐
│   Flask + Gunicorn (2 workers)        │
│   ┌────────────┬───────────────────┐ │
│   │ REST API   │ SocketIO WebSocket │ │
│   └────────────┴───────────────────┘ │
└──────────────┬───────────────────────┘
               │
┌──────────────▼───────────────────────┐
│    PostgreSQL 15 (Alpine)             │
│  数据库 (~400MB)                      │
│  持久化存储卷 (不会丢数据)             │
└──────────────────────────────────────┘

  本地存储:
  /backend/uploads/  ← 合同附件 (~15GB)
```

---

## 十、成本汇总

| 项目 | 月费用（预估） |
|------|--------------|
| 服务器 (2核4G 60GB) | **50 - 90 元** |
| 域名 (.com/.cn) | **~50 元/年** (约 4 元/月) |
| SSL 证书 | **免费** (Let's Encrypt) |
| **合计月成本** | **~54 - 94 元/月** |

---

> **文档版本**: v1.0 (小型团队版)
> **适用场景**: ~5,000 合同 / 7 人同时在线
> **最后更新**: 2026-04-22
