# VPS 部署

1. Ubuntu 24.04 安装 Docker Engine 与 Compose plugin。
2. 复制 `.env.example` 为 `.env`，设置强随机 `SECRET_KEY`、`DOMAIN`、`COOKIE_SECURE=true`。
3. 百炼模式设置 `AI_PROVIDER=dashscope`、业务空间专属 `DASHSCOPE_BASE_URL`、TTS URL、模型、音色和 API Key。
4. 运行 `docker compose up -d --build`。
5. 将教材原图和派生 WebP 导入 `textbook_pages` 卷；不要通过 Caddy 公开该卷。
6. 定时执行 `deploy/backup.ps1` 或使用等价 Linux 备份，备份数据库和教材导入报告。

生产环境必须确认课本扫描页的合法展示权。删除相关 `TextbookEdition` 数据和卷内目录即可下架。

