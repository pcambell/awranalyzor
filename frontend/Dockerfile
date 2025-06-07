# 多阶段构建 - 生产级React应用
FROM node:18-alpine as builder

# 设置工作目录
WORKDIR /app

# 复制package文件
COPY package*.json ./

# 安装依赖（使用npm ci以确保一致性）
RUN npm ci --only=production

# 复制源代码
COPY . .

# 构建生产版本
ENV NODE_ENV=production
RUN npm run build

# 生产镜像 - Nginx
FROM nginx:1.24-alpine as production

# 创建非root用户
RUN addgroup -g 1001 -S awrapp && \
    adduser -S awrapp -u 1001

# 安装curl用于健康检查
RUN apk add --no-cache curl

# 复制自定义Nginx配置
COPY nginx.conf /etc/nginx/nginx.conf
COPY default.conf /etc/nginx/conf.d/default.conf

# 从builder阶段复制构建文件
COPY --from=builder /app/build /usr/share/nginx/html

# 创建Nginx缓存目录并设置权限
RUN mkdir -p /var/cache/nginx /var/log/nginx /var/run && \
    chown -R awrapp:awrapp /var/cache/nginx /var/log/nginx /var/run /usr/share/nginx/html

# 切换到非root用户
USER awrapp

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/ || exit 1

# 暴露端口
EXPOSE 80

# 启动命令
CMD ["nginx", "-g", "daemon off;"] 