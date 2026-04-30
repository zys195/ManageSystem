# 合同管理系统 — 生产部署指南

> 适用规模：1 万合同 / 50 人以内同时在线

---

## 一、服务器推荐与购买

### 推荐配置（标准方案）

| 项目 | 配置 |
|------|------|
| CPU | **4 核** |
| 内存 | **8 GB** |
| 系统盘 | **80 GB SSD** |
| 数据盘（可选） | **100-200 GB SSD**（存附件文件） |
| 带宽 | **6 Mbps** |
| 操作系统 | **Ubuntu 22.04 LTS / CentOS 7.9** |

### 购买渠道推荐

#### 方案 A：腾讯云 Lighthouse（最省心）

1. 打开 https://cloud.tencent.com/product/lighthouse
2. 选择「轻量应用服务器」
3. 地域：选择离用户最近的区域
4. 镜像：**Docker 22.04** 或 **Ubuntu 22.04 LTS**
5. 配置：4 核 8GB 内存 120GB SSD
6. 带宽：6Mbps
7. 参考价：约 **100-150 元/月**
8. 新用户通常有优惠，首年可能低至 **50-70 元/月**

#### 方案 B：阿里云 ECS

1. 打开 https://ecs.console.aliyun.com/
2. 选择实例规格：`ecs.t6-c4m8.large`（4 核 8GB）或类似
3. 镜像：**Ubuntu 22.04 LTS**
4. 系统盘：40-80 GB ESSD
5. 数据盘：100 GB ESSD（存附件）
6. 带宽：按流量计费或固定带宽
7. 参考价：约 **150-250 元/月**

#### 方案 C：华为云 ECS

1. 打开 https://console.huaweicloud.com/ecm/
2. 规格：c6.xlarge.4（4 核 8GB）
3. 镜像：Ubuntu 22.04
4. 参考：约 **140-200 元/月**

### 购买后必做

1. 在云平台控制台设置**安全组/防火墙规则**，放行以下端口：
   - `80` — HTTP（前端访问）
   - `443` — HTTPS（如需 SSL）
   - `22` — SSH（远程连接）

2. 用 SSH 连接到服务器：
   ```
   ssh root@你的服务器IP
   ```

---

## 二、服务器环境准备

以下命令全部在服务器上以 **root 用户**执行。

### 第 1 步：系统基础更新

```bash
apt update && apt upgrade -y
```

### 第 2 步：安装 Docker 和 Docker Compose

```bash
# 安装依赖
apt install -y apt-transport-https ca-certificates curl gnupg lsb-release

# 添加 Docker 官方 GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# 添加 Docker 源
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list

# 安装 Docker
apt update && apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 启动并设置开机自启
systemctl enable --now docker
```

### 第 3 步：验证安装

```bash
docker --version          # 应显示 Docker version 24.x+
docker compose version    # 应显示 Docker Compose v2.x+
```

---

## 三、上传项目代码到服务器

### 方式 A：通过 Git 克隆（推荐）

```bash
# 安装 git
apt install -y git

# 进入部署目录
cd /opt

# 克隆你的仓库（替换为你的实际地址）
git clone https://github.com/你的用户名/FileManage.git contract-system

cd contract-system
```

### 方式 B：通过 SFTP 上传

用 WinSCP / FileZilla / FinalShell 等工具：
1. 连接服务器的 `/opt/` 目录
2. 上传整个项目文件夹，重命名为 `contract-system`
3. 确保上传了所有文件（注意 `.env` 文件也要传）

---

## 四、生产环境配置

### 第 1 步：创建环境变量文件

```bash
cd /opt/contract-system
```

创建 `.env` 生产配置文件：

```bash
cat > .env << 'EOF'
# ===== 合同管理系统 - 生产环境配置 =====

# 安全密钥（请修改为随机字符串！可以用 python -c "import secrets; print(secrets.token_hex(32))" 生成）
SECRET_KEY=请替换为32位随机十六进制串
JWT_SECRET_KEY=请替换为另一个32位随机十六进制串

# 数据库密码（PostgreSQL 内部通信密码，不需要外部访问）
DB_PASSWORD=ContractProd@2026!StrongPassword

# CORS 允许的域名（改成你实际的域名或 IP）
CORS_ORIGINS=http://你的域名或IP

# Flask 配置
FLASK_DEBUG=false
FLASK_HOST=0.0.0.0
FLASK_PORT=5000

# 协作编辑配置
COLLAB_EDIT_LOCK_TIMEOUT=300
COLLAB_HEARTBEAT_INTERVAL=15
COLLAB_MAX_ONLINE_USERS=100
EOF
```

> **重要**：务必把 `SECRET_KEY` 和 `JWT_SECRET_KEY` 改成随机值！

生成随机密钥的方法：
```bash
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32)); print('JWT_SECRET_KEY=' + secrets.token_hex(32))"
```

### 第 2 步：确保后端有 .env 文件

```bash
# 后端 config.py 会读取 backend/.env
cp .env backend/.env
```

### 第 3 步：修复 Nginx 代理端口（重要！）

当前 `frontend/nginx.conf` 中 API 代理指向 `7999`，但生产环境中后端使用 `5000`。需要统一：

确认 `frontend/nginx.conf` 中 API 代理目标为 **5000**：

```nginx
location /api {
    proxy_pass http://backend:5000;   # 必须是 5000
    ...
}

location /socket.io {
    proxy_pass http://backend:5000/socket.io;   # 必须是 5000
    ...
}
```

如果不对，在服务器上执行：
```bash
sed -i 's/backend:7999/backend:5000/g' frontend/nginx.conf
```

---

## 五、构建和启动所有服务

### 第 1 步：构建镜像

```bash
cd /opt/contract-system

# 构建所有镜像（首次较慢，约 5-10 分钟）
docker compose build
```

### 第 2 步：启动服务

```bash
# 启动所有容器（后台运行）
docker compose up -d

# 查看运行状态
docker compose ps
```

正常情况下应该看到 3 个容器全部 **running**：

```
NAME                    STATUS      PORTS
contract_system-db-1       running     5432/tcp
contract_system-backend-1  running     0.0.0.0:5000->5000/tcp
contract_system-frontend-1 running     0.0.0.0:80->80/tcp
```

### 第 3 步：初始化数据库

```bash
# 进入后端容器执行数据库初始化
docker compose exec backend flask --app run.py init-db

# 灌入测试数据（包含默认账号 admin/Admin123!）
docker compose exec backend flask --app run.py seed
```

### 第 4 步：验证启动

```bash
# 测试健康检查接口
curl http://127.0.0.1/api/health

# 应返回: {"message":"ok"}
```

然后在浏览器中打开 `http://你的服务器IP`，用 **admin / Admin123!** 登录。

---

## 六、域名绑定 + HTTPS（推荐）

### 第 1 步：购买域名并解析

1. 在域名服务商（腾讯云/阿里云等）购买域名，例如 `contract.yourcompany.com`
2. 添加 A 记录解析到服务器 IP：
   ```
   主机记录: @ 或 www
   记录类型: A
   记录值: 你的服务器公网IP
   TTL: 600
   ```

### 第 2 步：申请免费 SSL 证书（Let's Encrypt）

```bash
# 安装 certbot
apt install -y certbot python3-certbot-nginx

# 申请证书（替换为你的域名）
certbot --nginx -d contract.yourcompany.com -d www.contract.yourcompany.com

# 按提示选择是否自动 HTTP→HTTPS 重定向（建议选 2: Redirect）
```

certbot 会自动帮你：
- 下载并安装 SSL 证书
- 修改 Nginx 配置启用 HTTPS
- 设置自动续期定时任务

### 第 3 步：验证 HTTPS

浏览器打开 `https://contract.yourcompany.com`，确认锁头图标出现。

---

## 七、日常运维管理

### 常用命令速查

```bash
cd /opt/contract-system

# 查看日志（实时）
docker compose logs -f              # 所有服务日志
docker compose logs -f backend      # 仅后端日志
docker compose logs -f db           # 仅数据库日志

# 重启某个服务（不丢数据）
docker compose restart backend

# 全部重启
docker compose down && docker compose up -d

# 更新代码后重新部署
git pull
docker compose build && docker compose up -d
docker compose exec backend flask --app run.py seed  # 如需重新灌数据

# 备份数据库
docker compose exec db pg_dump -U contract_user contract_system > backup_$(date +%Y%m%d).sql

# 恢复数据库
cat backup_20260422.sql | docker compose exec -T db psql -U contract_user contract_system

# 查看磁盘占用
du -sh ./backend/uploads            # 附件大小
docker system df                     # Docker 占用
```

### 自动备份脚本（可选）

创建 `/opt/scripts/backup.sh`：

```bash
#!/bin/bash
# ===== 合同管理系统 - 每日备份 =====
BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# 备份数据库
cd /opt/contract-system
docker compose exec -T db pg_dump -U contract_user contract_system > "$BACKUP_DIR/db_$DATE.sql"

# 备份附件（增量压缩）
tar czf "$BACKUP_DIR/uploads_$DATE.tar.gz" -C /opt/contract-system backend/uploads/

# 清理 30 天前的备份
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "[$(date)] 备份完成: db_$DATE.sql, uploads_$DATE.tar.gz"
```

设置每日凌晨 3 点自动执行：
```bash
chmod +x /opt/scripts/backup.sh
echo "0 3 * * * /opt/scripts/backup.sh >> /var/log/backup.log 2>&1" | crontab -
```

---

## 八、监控与安全建议

### 8.1 安全加固清单

| 项目 | 说明 |
|------|------|
| 修改 SSH 默认端口 | 改掉 22 端口，降低扫描风险 |
| 禁止 root 密码登录 | 使用密钥认证 |
| 定期更新系统 | `apt update && apt upgrade` 每周一次 |
| 数据库端口不对外暴露 | 当前已通过内部网络隔离，5432 不映射到宿主机 |
| 定期更换 SECRET_KEY | 至少每季度更换一次 |

### 8.2 性能监控

```bash
# 实时查看资源占用（按 CPU 排序）
htop

# 查看 Docker 容器资源使用
docker stats --no-stream

# 查看磁盘空间
df -h
du -sh /opt/contract-system/*
```

### 8.3 告警阈值参考（4 核 8GB 机器）

| 指标 | 正常范围 | 告警阈值 |
|------|---------|---------|
| CPU 使用率 | < 50% | > 80% |
| 内存使用率 | < 70% | > 85% |
| 磁盘使用率 | < 60% | > 85% |
| 数据库连接数 | < 20 | > 50 |

---

## 九、故障排查

| 问题现象 | 可能原因 | 解决方法 |
|---------|---------|---------|
| 页面打不开 | 前端容器未启动 | `docker compose ps && docker compose restart frontend` |
| 登录报 500 | 数据库未初始化 | `docker compose exec backend flask --app run.py init-db` |
| 上传附件失败 | uploads 目录权限不足 | `chmod 777 backend/uploads` |
| WebSocket 断连 | Nginx 超时设置太短 | 检查 nginx.conf 的 proxy_read_timeout |
| 数据库连不上 | PostgreSQL 未就绪 | `docker compose restart db` 等 15 秒后再重启 backend |

---

## 十、架构图

```
                    ┌──────────────────────────┐
                    │        用户浏览器         │
                    │   https://你的域名        │
                    └────────────┬─────────────┘
                                 │ :443 (HTTPS)
                    ┌────────────▼─────────────┐
                    │    Nginx (SSL + 反向代理)  │
                    │   前端静态文件 + API 代理    │
                    └─────┬──────────┬──────────┘
                          │ /api/*   │ /socket.io*
                ┌─────────▼──────────▼──────────┐
                │   Flask + Gunicorn (4 workers)  │
                │     SocketIO WebSocket 支持     │
                └────────────┬──────────────────┘
                             │
                ┌────────────▼──────────────────┐
                │    PostgreSQL 15 (Alpine)       │
                │   数据库 + 文件存储持久化卷       │
                └────────────────────────────────┘
```

---

> **文档版本**: v1.0
> **适用项目**: FileManage（合同管理系统）
> **最后更新**: 2026-04-22
