#!/bin/bash

# Oracle AWR分析器 - 运维管理脚本
# 包含日常运维操作：启动、停止、重启、日志查看、备份等

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# 显示用法
show_usage() {
    echo "Oracle AWR分析器 - 运维管理脚本"
    echo ""
    echo "用法: $0 <命令> [选项]"
    echo ""
    echo "可用命令:"
    echo "  start         启动所有服务"
    echo "  stop          停止所有服务"
    echo "  restart       重启所有服务"
    echo "  status        显示服务状态"
    echo "  logs          查看日志"
    echo "  health        执行健康检查"
    echo "  backup        备份数据库"
    echo "  restore       恢复数据库"
    echo "  update        更新服务"
    echo "  shell         进入容器shell"
    echo "  cleanup       清理系统"
    echo "  monitor       监控系统资源"
    echo ""
    echo "选项:"
    echo "  --service <name>  指定服务名称"
    echo "  --follow          跟踪日志输出"
    echo "  --lines <num>     显示日志行数"
    echo "  --help            显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 start"
    echo "  $0 logs --service backend --follow"
    echo "  $0 shell --service backend"
    echo "  $0 backup"
}

# 启动服务
start_services() {
    local service="$1"
    
    if [ -n "$service" ]; then
        log_info "启动服务: $service"
        docker-compose up -d "$service"
    else
        log_info "启动所有服务..."
        docker-compose up -d
    fi
    
    log_success "服务启动完成"
    show_status
}

# 停止服务
stop_services() {
    local service="$1"
    
    if [ -n "$service" ]; then
        log_info "停止服务: $service"
        docker-compose stop "$service"
    else
        log_info "停止所有服务..."
        docker-compose down
    fi
    
    log_success "服务停止完成"
}

# 重启服务
restart_services() {
    local service="$1"
    
    if [ -n "$service" ]; then
        log_info "重启服务: $service"
        docker-compose restart "$service"
    else
        log_info "重启所有服务..."
        docker-compose down
        docker-compose up -d
    fi
    
    log_success "服务重启完成"
    show_status
}

# 显示服务状态
show_status() {
    log_info "服务状态:"
    docker-compose ps
    
    echo ""
    log_info "系统资源使用:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
}

# 查看日志
show_logs() {
    local service="$1"
    local follow="$2"
    local lines="$3"
    
    local cmd="docker-compose logs"
    
    if [ -n "$lines" ]; then
        cmd="$cmd --tail=$lines"
    else
        cmd="$cmd --tail=100"
    fi
    
    if [ "$follow" = "true" ]; then
        cmd="$cmd -f"
    fi
    
    if [ -n "$service" ]; then
        cmd="$cmd $service"
    fi
    
    log_info "显示日志: $service"
    eval $cmd
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    local endpoints=(
        "http://localhost/api/health/"
        "http://localhost/api/ready/"
        "http://localhost/api/live/"
    )
    
    for endpoint in "${endpoints[@]}"; do
        if curl -f "$endpoint" > /dev/null 2>&1; then
            log_success "✓ $endpoint"
        else
            log_error "✗ $endpoint"
        fi
    done
    
    # 检查Docker容器状态
    echo ""
    log_info "容器状态检查:"
    docker-compose ps --format "table {{.Name}}\t{{.State}}\t{{.Status}}"
}

# 备份数据库
backup_database() {
    local backup_dir="./backups"
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local backup_file="$backup_dir/awranalyzor_backup_$timestamp.sql"
    
    # 创建备份目录
    mkdir -p "$backup_dir"
    
    log_info "开始数据库备份..."
    
    # 执行备份
    docker-compose exec -T db pg_dump -U awruser awranalyzor > "$backup_file"
    
    if [ $? -eq 0 ]; then
        # 压缩备份文件
        gzip "$backup_file"
        log_success "数据库备份完成: ${backup_file}.gz"
        
        # 显示备份文件大小
        local size=$(du -h "${backup_file}.gz" | cut -f1)
        log_info "备份文件大小: $size"
    else
        log_error "数据库备份失败"
        exit 1
    fi
}

# 恢复数据库
restore_database() {
    local backup_file="$1"
    
    if [ -z "$backup_file" ]; then
        log_error "请指定备份文件"
        echo "用法: $0 restore <backup_file>"
        exit 1
    fi
    
    if [ ! -f "$backup_file" ]; then
        log_error "备份文件不存在: $backup_file"
        exit 1
    fi
    
    log_warning "警告: 此操作将覆盖当前数据库!"
    echo "确认继续? (y/N)"
    read -r confirm
    
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        log_info "操作已取消"
        exit 0
    fi
    
    log_info "开始数据库恢复..."
    
    # 检查文件是否压缩
    if [[ "$backup_file" == *.gz ]]; then
        zcat "$backup_file" | docker-compose exec -T db psql -U awruser awranalyzor
    else
        cat "$backup_file" | docker-compose exec -T db psql -U awruser awranalyzor
    fi
    
    if [ $? -eq 0 ]; then
        log_success "数据库恢复完成"
    else
        log_error "数据库恢复失败"
        exit 1
    fi
}

# 更新服务
update_services() {
    log_info "更新服务..."
    
    # 拉取最新代码
    if [ -d ".git" ]; then
        log_info "拉取最新代码..."
        git pull
    fi
    
    # 重新构建镜像
    log_info "重新构建镜像..."
    docker-compose build
    
    # 重启服务
    log_info "重启服务..."
    docker-compose down
    docker-compose up -d
    
    # 执行迁移
    log_info "执行数据库迁移..."
    docker-compose exec backend python manage.py migrate
    
    # 收集静态文件
    log_info "收集静态文件..."
    docker-compose exec backend python manage.py collectstatic --noinput
    
    log_success "服务更新完成"
}

# 进入容器shell
enter_shell() {
    local service="$1"
    
    if [ -z "$service" ]; then
        service="backend"
    fi
    
    log_info "进入容器shell: $service"
    docker-compose exec "$service" /bin/bash
}

# 清理系统
cleanup_system() {
    log_warning "系统清理操作"
    echo "这将清理未使用的镜像、容器和数据卷"
    echo "确认继续? (y/N)"
    read -r confirm
    
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        log_info "操作已取消"
        exit 0
    fi
    
    log_info "清理Docker资源..."
    
    # 清理停止的容器
    docker container prune -f
    
    # 清理未使用的镜像
    docker image prune -f
    
    # 清理未使用的网络
    docker network prune -f
    
    # 清理未使用的数据卷（谨慎操作）
    echo "是否清理未使用的数据卷? 这可能删除重要数据! (y/N)"
    read -r confirm_volume
    
    if [ "$confirm_volume" = "y" ] || [ "$confirm_volume" = "Y" ]; then
        docker volume prune -f
    fi
    
    log_success "系统清理完成"
}

# 监控系统资源
monitor_system() {
    log_info "系统资源监控 (按Ctrl+C退出)"
    
    while true; do
        clear
        echo "=== Oracle AWR分析器 - 系统监控 ==="
        echo "时间: $(date)"
        echo ""
        
        # Docker容器状态
        echo "=== 容器状态 ==="
        docker-compose ps --format "table {{.Name}}\t{{.State}}\t{{.Status}}"
        echo ""
        
        # 资源使用情况
        echo "=== 资源使用 ==="
        docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
        echo ""
        
        # 系统负载
        echo "=== 系统负载 ==="
        uptime
        echo ""
        
        # 磁盘使用
        echo "=== 磁盘使用 ==="
        df -h / | head -2
        echo ""
        
        sleep 5
    done
}

# 主函数
main() {
    local command="$1"
    shift
    
    # 解析参数
    local service=""
    local follow=false
    local lines=""
    
    while [ $# -gt 0 ]; do
        case $1 in
            --service)
                service="$2"
                shift 2
                ;;
            --follow)
                follow=true
                shift
                ;;
            --lines)
                lines="$2"
                shift 2
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                # 对于restore命令，第一个参数是备份文件
                if [ "$command" = "restore" ] && [ -z "$service" ]; then
                    service="$1"
                fi
                shift
                ;;
        esac
    done
    
    # 检查Docker Compose文件
    if [ ! -f "docker-compose.yml" ]; then
        log_error "docker-compose.yml文件不存在"
        exit 1
    fi
    
    # 执行命令
    case $command in
        start)
            start_services "$service"
            ;;
        stop)
            stop_services "$service"
            ;;
        restart)
            restart_services "$service"
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "$service" "$follow" "$lines"
            ;;
        health)
            health_check
            ;;
        backup)
            backup_database
            ;;
        restore)
            restore_database "$service"
            ;;
        update)
            update_services
            ;;
        shell)
            enter_shell "$service"
            ;;
        cleanup)
            cleanup_system
            ;;
        monitor)
            monitor_system
            ;;
        *)
            log_error "未知命令: $command"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@" 