#!/bin/bash
# AWR分析系统 - 生产环境管理脚本
# {{CHENGQI: P3-LD-018 性能优化和监控 - 生产管理脚本 - 2025-06-10T20:40:00 +08:00}}

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
ENV_FILE=".env.production"
BACKUP_DIR="./backups"
LOG_DIR="./logs"

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 检查服务状态
check_status() {
    log_info "检查AWR分析系统状态..."
    
    echo "===================="
    echo "Docker容器状态："
    docker-compose --env-file $ENV_FILE ps
    echo ""
    
    echo "系统健康检查："
    if curl -s http://localhost/api/health/ | jq -r '.status' 2>/dev/null; then
        log_success "系统健康检查通过"
    else
        log_warning "健康检查失败或jq未安装"
        curl -s http://localhost/api/health/ || log_error "无法访问健康检查端点"
    fi
    echo ""
    
    echo "磁盘使用情况："
    df -h | grep -E "Filesystem|/dev/"
    echo ""
    
    echo "内存使用情况："
    free -h
}

# 查看日志
view_logs() {
    local service=${1:-""}
    
    if [ -z "$service" ]; then
        log_info "可用的服务：backend, frontend, celery_worker, celery_beat, db, redis"
        log_info "用法: $0 logs <service_name>"
        return 1
    fi
    
    log_info "查看 $service 服务日志..."
    docker-compose --env-file $ENV_FILE logs -f --tail=100 $service
}

# 数据库备份
backup_database() {
    log_info "开始数据库备份..."
    
    # 创建备份目录
    mkdir -p $BACKUP_DIR
    
    # 生成备份文件名
    BACKUP_FILE="$BACKUP_DIR/awranalyzor_backup_$(date +%Y%m%d_%H%M%S).sql"
    
    # 执行备份
    docker-compose --env-file $ENV_FILE exec -T db pg_dump -U awruser awranalyzor > $BACKUP_FILE
    
    if [ $? -eq 0 ]; then
        log_success "数据库备份完成: $BACKUP_FILE"
        
        # 压缩备份文件
        gzip $BACKUP_FILE
        log_success "备份文件已压缩: ${BACKUP_FILE}.gz"
        
        # 清理旧备份（保留最近7天）
        find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
        log_info "已清理7天前的旧备份文件"
    else
        log_error "数据库备份失败"
        return 1
    fi
}

# 恢复数据库
restore_database() {
    local backup_file=$1
    
    if [ -z "$backup_file" ]; then
        log_error "请指定备份文件"
        log_info "用法: $0 restore-db <backup_file>"
        return 1
    fi
    
    if [ ! -f "$backup_file" ]; then
        log_error "备份文件不存在: $backup_file"
        return 1
    fi
    
    log_warning "⚠️  这将覆盖当前数据库！按Enter继续，Ctrl+C取消..."
    read
    
    log_info "恢复数据库从: $backup_file"
    
    # 停止相关服务
    docker-compose --env-file $ENV_FILE stop backend celery_worker celery_beat
    
    # 恢复数据库
    if [[ $backup_file == *.gz ]]; then
        zcat $backup_file | docker-compose --env-file $ENV_FILE exec -T db psql -U awruser -d awranalyzor
    else
        cat $backup_file | docker-compose --env-file $ENV_FILE exec -T db psql -U awruser -d awranalyzor
    fi
    
    if [ $? -eq 0 ]; then
        log_success "数据库恢复完成"
        
        # 重启服务
        docker-compose --env-file $ENV_FILE up -d
        log_success "服务已重启"
    else
        log_error "数据库恢复失败"
        return 1
    fi
}

# 重启服务
restart_service() {
    local service=${1:-"all"}
    
    if [ "$service" = "all" ]; then
        log_info "重启所有服务..."
        docker-compose --env-file $ENV_FILE restart
    else
        log_info "重启 $service 服务..."
        docker-compose --env-file $ENV_FILE restart $service
    fi
    
    log_success "服务重启完成"
}

# 更新系统
update_system() {
    log_info "更新AWR分析系统..."
    
    # 备份数据库
    backup_database
    
    # 拉取最新代码
    log_info "拉取最新代码..."
    git pull origin main
    
    # 重新构建镜像
    log_info "重新构建Docker镜像..."
    docker-compose --env-file $ENV_FILE build --no-cache
    
    # 运行数据库迁移
    log_info "运行数据库迁移..."
    docker-compose --env-file $ENV_FILE run --rm backend python manage.py migrate
    
    # 收集静态文件
    log_info "收集静态文件..."
    docker-compose --env-file $ENV_FILE run --rm backend python manage.py collectstatic --noinput
    
    # 重启服务
    log_info "重启服务..."
    docker-compose --env-file $ENV_FILE up -d
    
    log_success "系统更新完成"
}

# 清理系统
cleanup_system() {
    log_info "清理系统资源..."
    
    # 清理Docker镜像
    log_info "清理未使用的Docker镜像..."
    docker image prune -f
    
    # 清理Docker容器
    log_info "清理已停止的Docker容器..."
    docker container prune -f
    
    # 清理Docker网络
    log_info "清理未使用的Docker网络..."
    docker network prune -f
    
    # 清理Docker卷（谨慎操作）
    log_warning "清理未使用的Docker卷（会删除孤立的数据）..."
    docker volume prune -f
    
    # 清理应用日志（保留最近30天）
    if [ -d "$LOG_DIR" ]; then
        log_info "清理应用日志文件（保留30天）..."
        find $LOG_DIR -name "*.log*" -mtime +30 -delete
    fi
    
    log_success "系统清理完成"
}

# 性能监控
monitor_performance() {
    log_info "AWR分析系统性能监控"
    echo "===================="
    
    # CPU使用率
    echo "CPU使用率："
    top -bn1 | grep "Cpu(s)" | awk '{print $2 + $4"%"}'
    
    # 内存使用率
    echo "内存使用率："
    free | grep Mem | awk '{printf "%.2f%%\n", $3/$2 * 100.0}'
    
    # 磁盘使用率
    echo "磁盘使用率："
    df -h | awk '$NF=="/"{printf "%s\n", $5}'
    
    # Docker容器资源使用
    echo ""
    echo "Docker容器资源使用："
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
    
    # 数据库连接数
    echo ""
    echo "数据库连接数："
    docker-compose --env-file $ENV_FILE exec -T db psql -U awruser -d awranalyzor -c "SELECT count(*) as connections FROM pg_stat_activity WHERE datname='awranalyzor';" | grep -E "^\s*[0-9]+"
    
    # AWR报告统计
    echo ""
    echo "AWR报告统计："
    curl -s http://localhost/api/dashboard/statistics/ | jq -r 'to_entries[] | "\(.key): \(.value)"' 2>/dev/null || echo "无法获取统计信息"
}

# 启用监控服务（Flower）
enable_monitoring() {
    log_info "启用Celery监控服务 (Flower)..."
    docker-compose --env-file $ENV_FILE --profile monitoring up -d flower
    log_success "Flower监控已启动，访问地址: http://localhost:5555"
}

# 禁用监控服务
disable_monitoring() {
    log_info "禁用监控服务..."
    docker-compose --env-file $ENV_FILE stop flower
    docker-compose --env-file $ENV_FILE rm -f flower
    log_success "监控服务已禁用"
}

# 显示帮助信息
show_help() {
    echo "AWR分析系统生产环境管理工具"
    echo ""
    echo "用法: $0 <command> [options]"
    echo ""
    echo "可用命令："
    echo "  status                    - 检查系统状态"
    echo "  logs <service>           - 查看服务日志"
    echo "  backup-db                - 备份数据库"
    echo "  restore-db <file>        - 恢复数据库"
    echo "  restart [service]        - 重启服务 (默认重启所有)"
    echo "  update                   - 更新系统"
    echo "  cleanup                  - 清理系统资源"
    echo "  monitor                  - 性能监控"
    echo "  enable-monitoring        - 启用Flower监控"
    echo "  disable-monitoring       - 禁用监控"
    echo "  help                     - 显示此帮助信息"
    echo ""
    echo "示例："
    echo "  $0 status                # 检查系统状态"
    echo "  $0 logs backend          # 查看后端日志"
    echo "  $0 backup-db             # 备份数据库"
    echo "  $0 restart frontend      # 重启前端服务"
}

# 主函数
main() {
    case "${1:-}" in
        status)
            check_status
            ;;
        logs)
            view_logs $2
            ;;
        backup-db)
            backup_database
            ;;
        restore-db)
            restore_database $2
            ;;
        restart)
            restart_service $2
            ;;
        update)
            update_system
            ;;
        cleanup)
            cleanup_system
            ;;
        monitor)
            monitor_performance
            ;;
        enable-monitoring)
            enable_monitoring
            ;;
        disable-monitoring)
            disable_monitoring
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "未知命令: ${1:-}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@" 