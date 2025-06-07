# Oracle AWR分析器 - 生产环境部署指南

## 概述

本文档提供Oracle AWR分析器生产环境的完整部署指南，包含Docker容器化部署、配置管理、监控和运维操作。

## 系统要求

### 硬件要求
- **CPU**: 最少4核，推荐8核
- **内存**: 最少8GB，推荐16GB  
- **存储**: 最少50GB可用空间，推荐100GB以上
- **网络**: 稳定的互联网连接

### 软件要求
- **操作系统**: Linux (Ubuntu 18.04+, CentOS 7+, RHEL 7+)
- **Docker**: 20.10+
- **Docker Compose**: 1.29+
- **Git**: 2.0+

## 快速部署

### 1. 获取源代码

```bash
git clone https://github.com/your-org/awranalyzor.git
cd awranalyzor
```

### 2. 配置环境变量

```bash
# 复制环境配置模板
cp env.production.example .env

# 编辑配置文件
vi .env
```

### 3. 执行一键部署

```bash
# 基础部署
./scripts/deploy.sh

# 包含监控的部署
./scripts/deploy.sh --monitoring

# 包含负载均衡的部署
./scripts/deploy.sh --loadbalancer

# 清理旧资源的部署
./scripts/deploy.sh --cleanup
```

## 详细部署步骤

### 1. 环境准备

#### 安装Docker
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install docker.io docker-compose

# CentOS/RHEL
sudo yum install docker docker-compose

# 启动Docker服务
sudo systemctl enable docker
sudo systemctl start docker
```

#### 配置用户权限
```bash
# 将当前用户添加到docker组
sudo usermod -aG docker $USER

# 重新登录或执行
newgrp docker
```

### 2. 配置管理

#### 环境变量配置
`.env`文件包含所有生产环境配置：

```env
# 数据库配置
DB_PASSWORD=strong_password_here
POSTGRES_DB=awranalyzor
POSTGRES_USER=awruser

# Redis配置
REDIS_PASSWORD=redis_password_here

# Django配置
SECRET_KEY=your_secret_key_here
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# 邮件配置
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

#### SSL证书配置
```bash
# 将SSL证书文件放置到指定目录
mkdir -p ssl/
cp your-cert.pem ssl/
cp your-key.pem ssl/

# 更新环境变量
SSL_CERTIFICATE_PATH=/app/ssl/your-cert.pem
SSL_PRIVATE_KEY_PATH=/app/ssl/your-key.pem
```

### 3. 服务架构

#### 核心服务组件
- **Frontend**: React应用 (Nginx)
- **Backend**: Django API服务器
- **Database**: PostgreSQL数据库
- **Cache**: Redis缓存
- **Worker**: Celery异步任务
- **Beat**: Celery定时任务调度器

#### 可选服务组件
- **Flower**: Celery任务监控
- **Nginx LB**: 负载均衡器
- **Monitoring**: 系统监控

### 4. 网络和端口

#### 默认端口配置
```
80   - 前端应用 (Nginx)
8000 - 后端API (Django)
5432 - PostgreSQL数据库
6379 - Redis缓存
5555 - Flower监控 (可选)
8080 - 负载均衡器 (可选)
```

#### 防火墙配置
```bash
# 开放必要端口
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw enable
```

## 运维管理

### 日常操作

#### 使用管理脚本
```bash
# 查看服务状态
./scripts/manage.sh status

# 启动/停止服务
./scripts/manage.sh start
./scripts/manage.sh stop
./scripts/manage.sh restart

# 查看日志
./scripts/manage.sh logs
./scripts/manage.sh logs --service backend --follow

# 进入容器
./scripts/manage.sh shell --service backend

# 系统监控
./scripts/manage.sh monitor
```

#### 健康检查
```bash
# 执行健康检查
./scripts/manage.sh health

# 或直接访问API
curl http://localhost/api/health/
curl http://localhost/api/ready/
curl http://localhost/api/live/
```

### 备份和恢复

#### 数据库备份
```bash
# 创建备份
./scripts/manage.sh backup

# 备份文件位置
ls -la backups/
```

#### 数据库恢复
```bash
# 恢复数据库
./scripts/manage.sh restore backups/awranalyzor_backup_20231201_143022.sql.gz
```

#### 自动备份配置
```bash
# 添加到crontab
crontab -e

# 每天凌晨2点自动备份
0 2 * * * cd /path/to/awranalyzor && ./scripts/manage.sh backup > /dev/null 2>&1
```

### 更新部署

#### 应用更新
```bash
# 更新代码和重启服务
./scripts/manage.sh update

# 或手动更新
git pull
docker-compose build
docker-compose down
docker-compose up -d
```

#### 数据库迁移
```bash
# 执行数据库迁移
docker-compose exec backend python manage.py migrate

# 查看迁移状态
docker-compose exec backend python manage.py showmigrations
```

## 监控和日志

### 日志管理

#### 查看实时日志
```bash
# 所有服务日志
docker-compose logs -f

# 特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
```

#### 日志文件位置
```
backend/logs/awr_analysis.log - 应用日志
backend/logs/errors.log       - 错误日志
```

### 性能监控

#### 系统资源监控
```bash
# 容器资源使用
docker stats

# 系统资源监控
./scripts/manage.sh monitor
```

#### Flower监控界面
访问 `http://localhost:5555` 查看Celery任务状态

### 告警配置

#### 设置Sentry错误监控
```env
# 在.env文件中添加
SENTRY_DSN=https://your-sentry-dsn
```

#### 系统告警脚本
```bash
#!/bin/bash
# health_alert.sh - 健康检查告警

if ! curl -f http://localhost/api/health/ > /dev/null 2>&1; then
    echo "AWR分析器健康检查失败" | mail -s "服务告警" admin@your-domain.com
fi
```

## 安全配置

### 网络安全

#### HTTPS配置
```yaml
# docker-compose.yml 中启用SSL
services:
  nginx:
    ports:
      - "443:443"
    volumes:
      - ./ssl:/etc/ssl/certs
```

#### 安全Headers
已在Nginx配置中启用：
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- X-XSS-Protection: 1; mode=block

### 访问控制

#### 管理后台保护
```nginx
# 限制管理后台访问IP
location /admin/ {
    allow 192.168.1.0/24;
    deny all;
    proxy_pass http://backend_pool;
}
```

#### 文件上传限制
```yaml
# 在docker-compose.yml中设置
environment:
  - MAX_FILE_SIZE=50MB
  - ALLOWED_FILE_TYPES=.html,.htm
```

## 故障排除

### 常见问题

#### 1. 服务启动失败
```bash
# 查看错误日志
docker-compose logs backend

# 检查配置文件
docker-compose config

# 重新构建镜像
docker-compose build --no-cache
```

#### 2. 数据库连接失败
```bash
# 检查数据库状态
docker-compose exec db pg_isready -U awruser

# 查看数据库日志
docker-compose logs db

# 重置数据库密码
docker-compose exec db psql -U awruser -c "ALTER USER awruser PASSWORD 'new_password';"
```

#### 3. Redis连接失败
```bash
# 检查Redis状态
docker-compose exec redis redis-cli ping

# 查看Redis日志
docker-compose logs redis
```

#### 4. 前端404错误
```bash
# 检查Nginx配置
docker-compose exec frontend nginx -t

# 重新构建前端
docker-compose build frontend
```

### 诊断工具

#### 系统诊断脚本
```bash
#!/bin/bash
# diagnose.sh - 系统诊断

echo "=== 系统诊断报告 ==="
echo "时间: $(date)"
echo ""

echo "=== Docker版本 ==="
docker --version
docker-compose --version

echo "=== 容器状态 ==="
docker-compose ps

echo "=== 系统资源 ==="
df -h
free -h
uptime

echo "=== 网络连接 ==="
netstat -tlnp | grep -E "(80|443|8000|5432|6379)"

echo "=== 健康检查 ==="
curl -s http://localhost/api/health/ | jq .
```

## 性能优化

### 数据库优化

#### PostgreSQL配置优化
```sql
-- 连接到数据库
docker-compose exec db psql -U awruser awranalyzor

-- 查看连接数
SELECT count(*) FROM pg_stat_activity;

-- 优化查询性能
EXPLAIN ANALYZE SELECT * FROM awr_upload_awrfile LIMIT 10;
```

### 缓存优化

#### Redis内存优化
```bash
# 查看Redis内存使用
docker-compose exec redis redis-cli info memory

# 设置内存限制
# 在docker-compose.yml中添加
services:
  redis:
    deploy:
      resources:
        limits:
          memory: 1G
```

### 应用优化

#### Django性能调优
```python
# 在生产环境设置中
DATABASES = {
    'default': {
        'CONN_MAX_AGE': 600,  # 连接池
        'OPTIONS': {
            'MAX_CONNS': 20,   # 最大连接数
        }
    }
}

# 启用查询缓存
CACHES = {
    'default': {
        'TIMEOUT': 300,  # 5分钟缓存
    }
}
```

## 扩展部署

### 水平扩展

#### 多实例部署
```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      replicas: 3  # 3个后端实例
      
  celery_worker:
    deploy:
      replicas: 2  # 2个Worker实例
```

#### 负载均衡配置
```nginx
# nginx/nginx_lb.conf
upstream backend_pool {
    least_conn;
    server backend1:8000 max_fails=3 fail_timeout=30s;
    server backend2:8000 max_fails=3 fail_timeout=30s;
    server backend3:8000 max_fails=3 fail_timeout=30s;
}
```

### 数据库集群

#### PostgreSQL主从复制
```yaml
services:
  db_master:
    image: postgres:15-alpine
    environment:
      POSTGRES_REPLICATION_MODE: master
      
  db_slave:
    image: postgres:15-alpine
    environment:
      POSTGRES_REPLICATION_MODE: slave
      POSTGRES_MASTER_SERVICE: db_master
```

## 附录

### 环境变量参考

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DB_PASSWORD` | 数据库密码 | - |
| `REDIS_PASSWORD` | Redis密码 | - |
| `SECRET_KEY` | Django密钥 | - |
| `DEBUG` | 调试模式 | `False` |
| `ALLOWED_HOSTS` | 允许的主机 | `localhost` |

### 端口映射参考

| 服务 | 内部端口 | 外部端口 | 说明 |
|------|----------|----------|------|
| Frontend | 80 | 80 | 前端应用 |
| Backend | 8000 | - | 后端API |
| Database | 5432 | - | PostgreSQL |
| Redis | 6379 | - | 缓存服务 |
| Flower | 5555 | 5555 | 任务监控 |

### 有用的命令

```bash
# 查看容器大小
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

# 清理Docker系统
docker system df
docker system prune -a

# 导出/导入镜像
docker save awranalyzor_backend > backend.tar
docker load < backend.tar

# 容器资源限制
docker-compose up -d --scale backend=3

# 实时监控日志
tail -f backend/logs/awr_analysis.log
```

---

**联系信息**
- 技术支持: tech-support@your-domain.com  
- 文档版本: v1.0
- 最后更新: 2024-01-01 