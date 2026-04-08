/**
 * PM2 配置文件
 * 用于生产环境进程管理
 */

module.exports = {
    apps: [{
        name: 'reits-platform',
        script: './backend/server.js',
        instances: 1,
        exec_mode: 'fork',
        
        // 环境变量
        env: {
            NODE_ENV: 'development',
            PORT: 3001
        },
        env_production: {
            NODE_ENV: 'production',
            PORT: 3001
        },
        
        // 日志配置
        log_file: './logs/combined.log',
        out_file: './logs/out.log',
        error_file: './logs/error.log',
        log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
        
        // 自动重启
        autorestart: true,
        max_restarts: 10,
        min_uptime: '10s',
        
        // 内存限制
        max_memory_restart: '500M',
        
        // 监控
        watch: false,
        ignore_watch: ['node_modules', 'logs', 'database/*.db*'],
        
        // 优雅关闭
        kill_timeout: 5000,
        listen_timeout: 3000,
        
        // 集群模式（可选）
        // instances: 'max',
        // exec_mode: 'cluster',
    }]
};
