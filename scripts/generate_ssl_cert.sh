#!/bin/bash
# AWR分析系统 - SSL证书生成脚本
# {{CHENGQI: P3-SE-017 生产安全配置 - SSL证书生成 - 2025-06-10T21:00:00 +08:00}}

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
SSL_DIR="./ssl_certs"
DOMAIN=${1:-"localhost"}
DAYS=${2:-365}

# 创建SSL目录
create_ssl_directory() {
    log_info "创建SSL证书目录..."
    mkdir -p $SSL_DIR
    chmod 700 $SSL_DIR
}

# 生成DH参数
generate_dhparam() {
    log_info "生成DH参数（这可能需要几分钟）..."
    
    if [ ! -f "$SSL_DIR/dhparam.pem" ]; then
        openssl dhparam -out $SSL_DIR/dhparam.pem 2048
        log_success "DH参数生成完成"
    else
        log_info "DH参数已存在，跳过生成"
    fi
}

# 生成自签名证书
generate_self_signed_cert() {
    log_info "为域名 $DOMAIN 生成自签名SSL证书（有效期${DAYS}天）..."
    
    # 创建证书配置文件
    cat > $SSL_DIR/cert.conf <<EOF
[req]
default_bits = 2048
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = CN
ST = Beijing
L = Beijing
O = AWR Analyzer
OU = IT Department
CN = $DOMAIN

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = $DOMAIN
DNS.2 = *.$DOMAIN
DNS.3 = localhost
IP.1 = 127.0.0.1
EOF

    # 生成私钥
    openssl genrsa -out $SSL_DIR/privkey.pem 2048
    
    # 生成证书签名请求
    openssl req -new -key $SSL_DIR/privkey.pem -out $SSL_DIR/cert.csr -config $SSL_DIR/cert.conf
    
    # 生成自签名证书
    openssl x509 -req -in $SSL_DIR/cert.csr -signkey $SSL_DIR/privkey.pem -out $SSL_DIR/fullchain.pem -days $DAYS -extensions v3_req -extfile $SSL_DIR/cert.conf
    
    # 清理临时文件
    rm $SSL_DIR/cert.csr $SSL_DIR/cert.conf
    
    # 设置权限
    chmod 600 $SSL_DIR/privkey.pem
    chmod 644 $SSL_DIR/fullchain.pem
    
    log_success "自签名SSL证书生成完成"
}

# 使用Let's Encrypt生成证书
generate_letsencrypt_cert() {
    local email=$1
    
    if [ -z "$email" ]; then
        log_error "使用Let's Encrypt需要提供邮箱地址"
        return 1
    fi
    
    log_info "使用Let's Encrypt为域名 $DOMAIN 生成SSL证书..."
    
    # 检查certbot是否安装
    if ! command -v certbot &> /dev/null; then
        log_error "certbot未安装，请先安装certbot"
        return 1
    fi
    
    # 生成证书
    certbot certonly \
        --standalone \
        --agree-tos \
        --no-eff-email \
        --email $email \
        -d $DOMAIN
    
    # 复制证书到SSL目录
    cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem $SSL_DIR/fullchain.pem
    cp /etc/letsencrypt/live/$DOMAIN/privkey.pem $SSL_DIR/privkey.pem
    
    # 设置权限
    chmod 600 $SSL_DIR/privkey.pem
    chmod 644 $SSL_DIR/fullchain.pem
    
    log_success "Let's Encrypt SSL证书生成完成"
}

# 验证证书
verify_certificate() {
    log_info "验证SSL证书..."
    
    if [ ! -f "$SSL_DIR/fullchain.pem" ] || [ ! -f "$SSL_DIR/privkey.pem" ]; then
        log_error "证书文件不存在"
        return 1
    fi
    
    # 检查证书有效性
    openssl x509 -in $SSL_DIR/fullchain.pem -text -noout > /tmp/cert_info.txt
    
    echo "证书信息："
    echo "=========="
    grep -A 1 "Subject:" /tmp/cert_info.txt
    grep -A 1 "Not Before:" /tmp/cert_info.txt
    grep -A 1 "Not After:" /tmp/cert_info.txt
    grep -A 5 "Subject Alternative Name:" /tmp/cert_info.txt || true
    
    # 验证私钥和证书匹配
    cert_hash=$(openssl x509 -noout -modulus -in $SSL_DIR/fullchain.pem | openssl md5)
    key_hash=$(openssl rsa -noout -modulus -in $SSL_DIR/privkey.pem | openssl md5)
    
    if [ "$cert_hash" = "$key_hash" ]; then
        log_success "证书和私钥匹配"
    else
        log_error "证书和私钥不匹配"
        return 1
    fi
    
    rm -f /tmp/cert_info.txt
}

# 设置自动续期
setup_auto_renewal() {
    log_info "设置SSL证书自动续期..."
    
    # 创建续期脚本
    cat > $SSL_DIR/renew_cert.sh <<'EOF'
#!/bin/bash
# SSL证书自动续期脚本

SSL_DIR="./ssl_certs"
DOMAIN=${1:-"localhost"}

# 检查证书过期时间
check_cert_expiry() {
    if [ -f "$SSL_DIR/fullchain.pem" ]; then
        expiry_date=$(openssl x509 -enddate -noout -in $SSL_DIR/fullchain.pem | cut -d= -f2)
        expiry_timestamp=$(date -d "$expiry_date" +%s)
        current_timestamp=$(date +%s)
        days_left=$(( (expiry_timestamp - current_timestamp) / 86400 ))
        
        echo "证书还有 $days_left 天过期"
        
        # 如果少于30天则续期
        if [ $days_left -lt 30 ]; then
            echo "证书即将过期，开始续期..."
            return 0
        else
            echo "证书还未到期，无需续期"
            return 1
        fi
    else
        echo "证书文件不存在"
        return 0
    fi
}

# 续期Let's Encrypt证书
renew_letsencrypt() {
    certbot renew --quiet
    
    if [ $? -eq 0 ]; then
        # 复制新证书
        cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem $SSL_DIR/fullchain.pem
        cp /etc/letsencrypt/live/$DOMAIN/privkey.pem $SSL_DIR/privkey.pem
        
        # 重启nginx
        docker-compose restart nginx
        
        echo "证书续期成功"
    else
        echo "证书续期失败"
        exit 1
    fi
}

# 主逻辑
if check_cert_expiry; then
    if command -v certbot &> /dev/null; then
        renew_letsencrypt
    else
        echo "需要手动续期证书"
    fi
fi
EOF

    chmod +x $SSL_DIR/renew_cert.sh
    
    log_success "自动续期脚本已创建: $SSL_DIR/renew_cert.sh"
    log_info "建议添加到cron中定期执行: 0 2 * * * /path/to/ssl_certs/renew_cert.sh"
}

# 显示帮助信息
show_help() {
    echo "AWR分析系统 SSL证书生成工具"
    echo ""
    echo "用法: $0 [选项] <domain> [days]"
    echo ""
    echo "选项:"
    echo "  --self-signed              生成自签名证书（默认）"
    echo "  --letsencrypt <email>      使用Let's Encrypt生成证书"
    echo "  --verify                   验证现有证书"
    echo "  --setup-renewal            设置自动续期"
    echo "  --help                     显示帮助信息"
    echo ""
    echo "参数:"
    echo "  domain                     域名（默认: localhost）"
    echo "  days                       证书有效期天数（默认: 365）"
    echo ""
    echo "示例:"
    echo "  $0 example.com             # 为example.com生成自签名证书"
    echo "  $0 --letsencrypt user@example.com example.com  # 使用Let's Encrypt"
    echo "  $0 --verify                # 验证现有证书"
}

# 主函数
main() {
    case "${1:-}" in
        --self-signed)
            shift
            DOMAIN=${1:-"localhost"}
            DAYS=${2:-365}
            create_ssl_directory
            generate_dhparam
            generate_self_signed_cert
            verify_certificate
            setup_auto_renewal
            ;;
        --letsencrypt)
            EMAIL=$2
            DOMAIN=${3:-"localhost"}
            if [ -z "$EMAIL" ]; then
                log_error "使用--letsencrypt选项需要提供邮箱地址"
                show_help
                exit 1
            fi
            create_ssl_directory
            generate_dhparam
            generate_letsencrypt_cert $EMAIL
            verify_certificate
            setup_auto_renewal
            ;;
        --verify)
            verify_certificate
            ;;
        --setup-renewal)
            setup_auto_renewal
            ;;
        --help|-h)
            show_help
            ;;
        *)
            # 默认生成自签名证书
            DOMAIN=${1:-"localhost"}
            DAYS=${2:-365}
            create_ssl_directory
            generate_dhparam
            generate_self_signed_cert
            verify_certificate
            setup_auto_renewal
            ;;
    esac
}

# 执行主函数
main "$@" 