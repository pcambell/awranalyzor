#!/bin/bash
# AWR分析系统 - 生产环境部署脚本
# {{CHENGQI: P3-LD-016 Docker容器化部署 - 生产部署脚本 - 2025-06-10T20:30:00 +08:00}}

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

# 检查必要的工具
check_requirements() {
    log_info "检查部署要求..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
    
    log_success "部署要求检查通过"
}

# 生成安全的密钥
generate_secret_key() {
    python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
}

# 创建生产环境配置
setup_production_env() {
    log_info "设置生产环境配置..."
    
    if [ ! -f .env.production ]; then
        log_warning ".env.production 不存在，从示例文件创建..."
        cp env.production.example .env.production
        
        # 生成安全的密钥
        SECRET_KEY=$(generate_secret_key)
        DB_PASSWORD=$(openssl rand -base64 32)
        REDIS_PASSWORD=$(openssl rand -base64 32)
        
        # 替换默认密钥
        sed -i "s/SECRET_KEY=.*/SECRET_KEY=${SECRET_KEY}/" .env.production
        sed -i "s/DB_PASSWORD=.*/DB_PASSWORD=${DB_PASSWORD}/" .env.production
        sed -i "s/REDIS_PASSWORD=.*/REDIS_PASSWORD=${REDIS_PASSWORD}/" .env.production
        
        log_success "生产环境配置已创建"
        log_warning "请编辑 .env.production 文件，设置您的域名和其他配置"
    else
        log_info ".env.production 已存在，跳过创建"
    fi
}

# 创建必要的目录
create_directories() {
    log_info "创建必要的目录..."
    
    mkdir -p logs
    mkdir -p media
    mkdir -p staticfiles
    mkdir -p database/init
    mkdir -p exports
    mkdir -p ssl_certs
    
    # 设置权限
    chmod 755 logs media staticfiles exports
    chmod 700 ssl_certs
    
    log_success "目录创建完成"
}

# 构建镜像
build_images() {
    log_info "构建Docker镜像..."
    
    # 设置环境变量文件
    export COMPOSE_FILE=docker-compose.yml
    export ENV_FILE=.env.production
    
    # 构建所有服务
    docker-compose --env-file .env.production build --no-cache
    
    log_success "Docker镜像构建完成"
}

# 数据库初始化
init_database() {
    log_info "初始化数据库..."
    
    # 启动数据库服务
    docker-compose --env-file .env.production up -d db redis
    
    # 等待数据库就绪
    log_info "等待数据库就绪..."
    sleep 10
    
    # 运行数据库迁移
    docker-compose --env-file .env.production run --rm backend python manage.py migrate
    
    # 创建超级用户（如果需要）
    if [ "$CREATE_SUPERUSER" = "true" ]; then
        log_info "创建超级用户..."
        docker-compose --env-file .env.production run --rm backend python manage.py createsuperuser --noinput --username admin --email admin@example.com || true
    fi
    
    # 收集静态文件
    docker-compose --env-file .env.production run --rm backend python manage.py collectstatic --noinput
    
    log_success "数据库初始化完成"
}

# 启动生产服务
start_production() {
    log_info "启动生产服务..."
    
    # 启动所有服务
    docker-compose --env-file .env.production up -d
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 15
    
    # 检查服务状态
    log_info "检查服务状态..."
    docker-compose --env-file .env.production ps
    
    log_success "生产服务启动完成"
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    # 检查后端健康
    if curl -f http://localhost/api/reports/ > /dev/null 2>&1; then
        log_success "后端服务健康"
    else
        log_error "后端服务不健康"
        return 1
    fi
    
    # 检查前端
    if curl -f http://localhost/ > /dev/null 2>&1; then
        log_success "前端服务健康"
    else
        log_error "前端服务不健康"
        return 1
    fi
    
    log_success "健康检查通过"
}

# 显示部署信息
show_deployment_info() {
    log_success "🎉 AWR分析系统部署完成！"
    echo ""
    echo "访问地址："
    echo "  前端界面: http://localhost"
    echo "  API接口: http://localhost/api/"
    echo ""
    echo "监控地址："
    echo "  Flower (Celery监控): http://localhost:5555 (需要启用monitoring profile)"
    echo ""
    echo "管理命令："
    echo "  查看日志: docker-compose --env-file .env.production logs -f [service_name]"
    echo "  重启服务: docker-compose --env-file .env.production restart [service_name]"
    echo "  停止所有服务: docker-compose --env-file .env.production down"
    echo ""
    echo "配置文件："
    echo "  生产环境配置: .env.production"
    echo "  Docker配置: docker-compose.yml"
}

# 主函数
main() {
    echo "🚀 AWR分析系统生产环境部署"
    echo "================================="
    
    # 检查部署参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --create-superuser)
                CREATE_SUPERUSER=true
                shift
                ;;
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --help)
                echo "用法: $0 [选项]"
                echo "选项:"
                echo "  --create-superuser  创建Django超级用户"
                echo "  --skip-build       跳过Docker镜像构建"
                echo "  --help             显示帮助信息"
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                exit 1
                ;;
        esac
    done
    
    # 执行部署步骤
    check_requirements
    setup_production_env
    create_directories
    
    if [ "$SKIP_BUILD" != "true" ]; then
        build_images
    fi
    
    init_database
    start_production
    health_check
    show_deployment_info
}

# 捕获错误并清理
trap 'log_error "部署失败，请检查错误信息"' ERR

# 执行主函数
main "$@" 