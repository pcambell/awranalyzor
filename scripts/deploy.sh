#!/bin/bash

# Oracle AWR分析器 - 一键部署脚本
# 包含环境检查、构建、启动和验证

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示banner
show_banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                Oracle AWR分析器 - 生产环境部署                ║"
    echo "║                     Production Deployment                    ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 检查Docker和Docker Compose
check_prerequisites() {
    log_info "检查系统依赖..."
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    
    # 检查Docker服务状态
    if ! docker info &> /dev/null; then
        log_error "Docker服务未运行，请启动Docker服务"
        exit 1
    fi
    
    log_success "系统依赖检查通过"
}

# 检查环境变量文件
check_environment() {
    log_info "检查环境配置..."
    
    if [ ! -f ".env" ]; then
        if [ -f "env.production.example" ]; then
            log_warning ".env文件不存在，复制示例文件..."
            cp env.production.example .env
            log_warning "请编辑.env文件配置生产环境参数"
            echo "编辑完成后按任意键继续..."
            read -n 1 -s
        else
            log_error "环境配置文件不存在，请创建.env文件"
            exit 1
        fi
    fi
    
    log_success "环境配置检查通过"
}

# 检查磁盘空间
check_disk_space() {
    log_info "检查磁盘空间..."
    
    # 检查可用空间（需要至少5GB）
    available_space=$(df / | awk 'NR==2 {print $4}')
    required_space=5242880  # 5GB in KB
    
    if [ "$available_space" -lt "$required_space" ]; then
        log_error "磁盘空间不足，至少需要5GB可用空间"
        exit 1
    fi
    
    log_success "磁盘空间检查通过 ($(($available_space/1024/1024))GB 可用)"
}

# 停止现有服务
stop_existing_services() {
    log_info "停止现有服务..."
    
    if docker-compose ps | grep -q "Up"; then
        docker-compose down
        log_success "现有服务已停止"
    else
        log_info "没有运行中的服务"
    fi
}

# 清理旧镜像（可选）
cleanup_old_images() {
    if [ "$1" = "--cleanup" ]; then
        log_info "清理旧镜像..."
        docker system prune -f
        docker volume prune -f
        log_success "镜像清理完成"
    fi
}

# 构建镜像
build_images() {
    log_info "构建Docker镜像..."
    
    # 构建后端镜像
    log_info "构建后端镜像..."
    docker-compose build backend
    
    # 构建前端镜像
    log_info "构建前端镜像..."
    docker-compose build frontend
    
    log_success "镜像构建完成"
}

# 启动数据库服务
start_database() {
    log_info "启动数据库服务..."
    
    docker-compose up -d db redis
    
    # 等待数据库启动
    log_info "等待数据库服务就绪..."
    sleep 10
    
    # 检查数据库健康状态
    local retries=30
    while [ $retries -gt 0 ]; do
        if docker-compose exec -T db pg_isready -U awruser -d awranalyzor; then
            log_success "数据库服务就绪"
            break
        fi
        retries=$((retries - 1))
        log_info "等待数据库启动... ($retries 次重试)"
        sleep 2
    done
    
    if [ $retries -eq 0 ]; then
        log_error "数据库启动超时"
        exit 1
    fi
}

# 运行数据库迁移
run_migrations() {
    log_info "运行数据库迁移..."
    
    # 临时启动后端容器执行迁移
    docker-compose run --rm backend python manage.py migrate
    
    log_success "数据库迁移完成"
}

# 创建超级用户（如果不存在）
create_superuser() {
    log_info "检查超级用户..."
    
    # 检查是否存在超级用户
    user_exists=$(docker-compose run --rm backend python manage.py shell -c "
from django.contrib.auth.models import User
print(User.objects.filter(is_superuser=True).exists())
" | tail -1)
    
    if [ "$user_exists" = "False" ]; then
        log_info "创建超级用户..."
        docker-compose run --rm backend python manage.py createsuperuser --noinput \
            --username admin \
            --email admin@example.com
        log_success "超级用户创建完成 (用户名: admin)"
    else
        log_info "超级用户已存在"
    fi
}

# 收集静态文件
collect_static() {
    log_info "收集静态文件..."
    
    docker-compose run --rm backend python manage.py collectstatic --noinput
    
    log_success "静态文件收集完成"
}

# 启动所有服务
start_services() {
    log_info "启动所有服务..."
    
    # 启动核心服务
    docker-compose up -d backend celery_worker celery_beat frontend
    
    log_success "服务启动完成"
}

# 启动监控服务（可选）
start_monitoring() {
    if [ "$1" = "--monitoring" ]; then
        log_info "启动监控服务..."
        docker-compose --profile monitoring up -d flower
        log_success "监控服务启动完成"
    fi
}

# 启动负载均衡器（可选）
start_loadbalancer() {
    if [ "$1" = "--loadbalancer" ]; then
        log_info "启动负载均衡器..."
        docker-compose --profile loadbalancer up -d nginx_lb
        log_success "负载均衡器启动完成"
    fi
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    local retries=30
    while [ $retries -gt 0 ]; do
        if curl -f http://localhost/api/health/ > /dev/null 2>&1; then
            log_success "应用健康检查通过"
            break
        fi
        retries=$((retries - 1))
        log_info "等待应用启动... ($retries 次重试)"
        sleep 3
    done
    
    if [ $retries -eq 0 ]; then
        log_error "应用健康检查失败"
        show_logs
        exit 1
    fi
}

# 显示服务状态
show_status() {
    log_info "服务状态:"
    docker-compose ps
    
    echo ""
    log_info "访问地址:"
    echo "  前端应用: http://localhost"
    echo "  后端API: http://localhost/api/"
    echo "  管理后台: http://localhost/admin/"
    
    if docker-compose ps | grep -q flower; then
        echo "  Celery监控: http://localhost:5555"
    fi
    
    if docker-compose ps | grep -q nginx_lb; then
        echo "  负载均衡器: http://localhost:8080"
    fi
}

# 显示日志
show_logs() {
    log_info "最近日志:"
    docker-compose logs --tail=50
}

# 主部署流程
main() {
    show_banner
    
    # 解析命令行参数
    local cleanup=false
    local monitoring=false
    local loadbalancer=false
    
    for arg in "$@"; do
        case $arg in
            --cleanup)
                cleanup=true
                ;;
            --monitoring)
                monitoring=true
                ;;
            --loadbalancer)
                loadbalancer=true
                ;;
            --help)
                echo "用法: $0 [选项]"
                echo "选项:"
                echo "  --cleanup      清理旧镜像和容器"
                echo "  --monitoring   启动监控服务 (Flower)"
                echo "  --loadbalancer 启动负载均衡器"
                echo "  --help         显示帮助信息"
                exit 0
                ;;
        esac
    done
    
    # 执行部署步骤
    check_prerequisites
    check_environment
    check_disk_space
    stop_existing_services
    
    if [ "$cleanup" = true ]; then
        cleanup_old_images --cleanup
    fi
    
    build_images
    start_database
    run_migrations
    create_superuser
    collect_static
    start_services
    
    if [ "$monitoring" = true ]; then
        start_monitoring --monitoring
    fi
    
    if [ "$loadbalancer" = true ]; then
        start_loadbalancer --loadbalancer
    fi
    
    health_check
    show_status
    
    log_success "🎉 AWR分析器部署完成！"
}

# 错误处理
trap 'log_error "部署过程中发生错误，请检查日志"; show_logs; exit 1' ERR

# 执行主函数
main "$@" 