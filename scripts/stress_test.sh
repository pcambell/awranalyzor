#!/bin/bash
# AWR分析系统 - 压力测试脚本
# {{CHENGQI: P3-TE-019 生产环境测试 - 压力测试 - 2025-06-10T21:10:00 +08:00}}

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 配置
BASE_URL="http://127.0.0.1"
CONCURRENT_USERS=${1:-10}
TEST_DURATION=${2:-60}
TEST_RESULTS_DIR="./test_results"

# 创建测试结果目录
mkdir -p $TEST_RESULTS_DIR

# 检查依赖
check_dependencies() {
    log_info "检查测试依赖..."
    
    if ! command -v curl &> /dev/null; then
        log_error "curl 未安装"
        exit 1
    fi
    
    if ! command -v ab &> /dev/null; then
        log_warning "Apache Bench (ab) 未安装，将使用curl进行基础测试"
        USE_AB=false
    else
        USE_AB=true
    fi
    
    log_success "依赖检查完成"
}

# 测试API健康状态
test_health_check() {
    log_info "测试健康检查端点..."
    
    response=$(curl -s -w "%{http_code}" -o /dev/null "$BASE_URL/api/health/")
    
    if [ "$response" = "200" ]; then
        log_success "健康检查通过 (HTTP $response)"
    else
        log_error "健康检查失败 (HTTP $response)"
        return 1
    fi
}

# 测试基础API功能
test_basic_apis() {
    log_info "测试基础API功能..."
    
    # 测试报告列表API
    log_info "测试报告列表API..."
    response=$(curl -s -w "%{http_code}" -o /tmp/reports_response.json "$BASE_URL/api/reports/")
    if [ "$response" = "200" ]; then
        report_count=$(cat /tmp/reports_response.json | grep -o '"id"' | wc -l)
        log_success "报告列表API正常 (找到 $report_count 个报告)"
    else
        log_error "报告列表API失败 (HTTP $response)"
    fi
    
    # 测试统计API
    log_info "测试统计API..."
    response=$(curl -s -w "%{http_code}" -o /tmp/stats_response.json "$BASE_URL/api/dashboard/statistics/")
    if [ "$response" = "200" ]; then
        log_success "统计API正常"
    else
        log_error "统计API失败 (HTTP $response)"
    fi
    
    # 清理临时文件
    rm -f /tmp/reports_response.json /tmp/stats_response.json
}

# 并发测试（使用Apache Bench）
concurrent_test_ab() {
    log_info "执行Apache Bench并发测试 ($CONCURRENT_USERS 并发用户, $TEST_DURATION 秒)..."
    
    # 测试主页
    log_info "测试主页并发访问..."
    ab -n $((CONCURRENT_USERS * 10)) -c $CONCURRENT_USERS -t $TEST_DURATION "$BASE_URL/" > $TEST_RESULTS_DIR/homepage_ab_test.txt 2>&1
    
    # 测试API端点
    log_info "测试API并发访问..."
    ab -n $((CONCURRENT_USERS * 10)) -c $CONCURRENT_USERS -t $TEST_DURATION "$BASE_URL/api/reports/" > $TEST_RESULTS_DIR/api_ab_test.txt 2>&1
    
    # 分析结果
    log_info "分析Apache Bench测试结果..."
    
    homepage_rps=$(grep "Requests per second" $TEST_RESULTS_DIR/homepage_ab_test.txt | awk '{print $4}')
    api_rps=$(grep "Requests per second" $TEST_RESULTS_DIR/api_ab_test.txt | awk '{print $4}')
    
    log_success "主页 RPS: $homepage_rps"
    log_success "API RPS: $api_rps"
    
    # 检查失败率
    homepage_failed=$(grep "Failed requests" $TEST_RESULTS_DIR/homepage_ab_test.txt | awk '{print $3}')
    api_failed=$(grep "Failed requests" $TEST_RESULTS_DIR/api_ab_test.txt | awk '{print $3}')
    
    if [ "$homepage_failed" = "0" ] && [ "$api_failed" = "0" ]; then
        log_success "并发测试：无失败请求"
    else
        log_warning "并发测试：主页失败 $homepage_failed 次, API失败 $api_failed 次"
    fi
}

# 并发测试（使用curl）
concurrent_test_curl() {
    log_info "执行curl并发测试 ($CONCURRENT_USERS 并发用户, $TEST_DURATION 秒)..."
    
    start_time=$(date +%s)
    end_time=$((start_time + TEST_DURATION))
    
    success_count=0
    error_count=0
    total_requests=0
    
    # 并发测试函数
    test_worker() {
        local worker_id=$1
        local worker_success=0
        local worker_error=0
        local worker_total=0
        
        while [ $(date +%s) -lt $end_time ]; do
            response=$(curl -s -w "%{http_code}" -o /dev/null "$BASE_URL/api/reports/")
            worker_total=$((worker_total + 1))
            
            if [ "$response" = "200" ]; then
                worker_success=$((worker_success + 1))
            else
                worker_error=$((worker_error + 1))
            fi
            
            sleep 0.1
        done
        
        echo "$worker_success $worker_error $worker_total" > $TEST_RESULTS_DIR/worker_$worker_id.txt
    }
    
    # 启动并发工作进程
    for i in $(seq 1 $CONCURRENT_USERS); do
        test_worker $i &
    done
    
    # 等待所有工作进程完成
    wait
    
    # 汇总结果
    for i in $(seq 1 $CONCURRENT_USERS); do
        if [ -f "$TEST_RESULTS_DIR/worker_$i.txt" ]; then
            worker_stats=$(cat $TEST_RESULTS_DIR/worker_$i.txt)
            worker_success=$(echo $worker_stats | awk '{print $1}')
            worker_error=$(echo $worker_stats | awk '{print $2}')
            worker_total=$(echo $worker_stats | awk '{print $3}')
            
            success_count=$((success_count + worker_success))
            error_count=$((error_count + worker_error))
            total_requests=$((total_requests + worker_total))
            
            rm -f $TEST_RESULTS_DIR/worker_$i.txt
        fi
    done
    
    # 计算统计数据
    actual_duration=$(($(date +%s) - start_time))
    rps=$((total_requests / actual_duration))
    success_rate=$((success_count * 100 / total_requests))
    
    log_success "总请求数: $total_requests"
    log_success "成功请求: $success_count"
    log_success "失败请求: $error_count"
    log_success "成功率: $success_rate%"
    log_success "平均RPS: $rps"
}

# 内存压力测试
memory_stress_test() {
    log_info "执行内存压力测试..."
    
    # 记录测试前的内存使用
    before_memory=$(free | grep Mem | awk '{printf "%.2f", $3/$2 * 100.0}')
    log_info "测试前内存使用率: $before_memory%"
    
    # 创建多个大请求来测试内存使用
    log_info "发送大量并发请求..."
    for i in {1..50}; do
        curl -s "$BASE_URL/api/reports/" > /dev/null &
        curl -s "$BASE_URL/api/dashboard/statistics/" > /dev/null &
    done
    
    # 等待请求完成
    wait
    
    # 记录测试后的内存使用
    after_memory=$(free | grep Mem | awk '{printf "%.2f", $3/$2 * 100.0}')
    log_info "测试后内存使用率: $after_memory%"
    
    # 检查内存使用是否在合理范围内
    memory_increase=$(echo "$after_memory - $before_memory" | bc -l 2>/dev/null || echo "0")
    if [ "${memory_increase%.*}" -lt 20 ]; then
        log_success "内存使用正常 (增长 ${memory_increase}%)"
    else
        log_warning "内存使用偏高 (增长 ${memory_increase}%)"
    fi
}

# 响应时间测试
response_time_test() {
    log_info "执行响应时间测试..."
    
    total_time=0
    request_count=100
    
    for i in $(seq 1 $request_count); do
        start_time=$(date +%s%N)
        curl -s "$BASE_URL/api/reports/" > /dev/null
        end_time=$(date +%s%N)
        
        duration=$(((end_time - start_time) / 1000000))  # 转换为毫秒
        total_time=$((total_time + duration))
        
        if [ $((i % 10)) -eq 0 ]; then
            log_info "完成 $i/$request_count 请求..."
        fi
    done
    
    avg_response_time=$((total_time / request_count))
    
    log_success "平均响应时间: ${avg_response_time}ms"
    
    if [ $avg_response_time -lt 500 ]; then
        log_success "响应时间符合要求 (<500ms)"
    else
        log_warning "响应时间较慢 (${avg_response_time}ms)"
    fi
}

# 数据库连接池测试
database_connection_test() {
    log_info "执行数据库连接池测试..."
    
    # 发送大量需要数据库查询的请求
    for i in {1..20}; do
        curl -s "$BASE_URL/api/reports/" > /dev/null &
        curl -s "$BASE_URL/api/dashboard/statistics/" > /dev/null &
    done
    
    wait
    
    # 检查数据库连接数
    connection_count=$(docker-compose exec -T db psql -U awruser -d awranalyzor -c "SELECT count(*) FROM pg_stat_activity WHERE datname='awranalyzor';" 2>/dev/null | grep -E "^\s*[0-9]+" | xargs)
    
    if [ ! -z "$connection_count" ]; then
        log_success "当前数据库连接数: $connection_count"
        
        if [ $connection_count -lt 50 ]; then
            log_success "数据库连接数正常"
        else
            log_warning "数据库连接数较高: $connection_count"
        fi
    else
        log_warning "无法获取数据库连接数"
    fi
}

# 生成测试报告
generate_test_report() {
    log_info "生成测试报告..."
    
    report_file="$TEST_RESULTS_DIR/stress_test_report_$(date +%Y%m%d_%H%M%S).txt"
    
    cat > $report_file <<EOF
AWR分析系统压力测试报告
======================

测试时间: $(date)
测试配置:
- 并发用户: $CONCURRENT_USERS
- 测试时长: $TEST_DURATION 秒
- 基础URL: $BASE_URL

测试结果摘要:
EOF
    
    if [ "$USE_AB" = true ] && [ -f "$TEST_RESULTS_DIR/homepage_ab_test.txt" ]; then
        echo "" >> $report_file
        echo "Apache Bench测试结果:" >> $report_file
        echo "=====================" >> $report_file
        grep -E "(Requests per second|Time per request|Failed requests)" $TEST_RESULTS_DIR/homepage_ab_test.txt >> $report_file 2>/dev/null || true
    fi
    
    echo "" >> $report_file
    echo "系统资源使用:" >> $report_file
    echo "============" >> $report_file
    echo "CPU使用率: $(top -bn1 | grep "Cpu(s)" | awk '{print $2 + $4"%"}' || echo "N/A")" >> $report_file
    echo "内存使用率: $(free | grep Mem | awk '{printf "%.2f%%", $3/$2 * 100.0}' || echo "N/A")" >> $report_file
    echo "磁盘使用率: $(df -h | awk '$NF=="/"{printf "%s", $5}' || echo "N/A")" >> $report_file
    
    log_success "测试报告已生成: $report_file"
}

# 主测试函数
main() {
    echo "🔥 AWR分析系统压力测试"
    echo "======================"
    echo "并发用户: $CONCURRENT_USERS"
    echo "测试时长: $TEST_DURATION 秒"
    echo ""
    
    check_dependencies
    test_health_check
    test_basic_apis
    
    if [ "$USE_AB" = true ]; then
        concurrent_test_ab
    else
        concurrent_test_curl
    fi
    
    memory_stress_test
    response_time_test
    database_connection_test
    generate_test_report
    
    log_success "🎉 压力测试完成！"
    log_info "查看详细结果: ls -la $TEST_RESULTS_DIR/"
}

# 捕获中断信号
trap 'log_warning "测试被中断"; exit 1' INT TERM

# 执行主函数
main "$@" 