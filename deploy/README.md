# VPS 部署

1. Ubuntu 24.04 安装 Docker Engine 与 Compose plugin。
2. 复制 `.env.example` 为 `.env`，设置强随机 `SECRET_KEY`、`DOMAIN`、`COOKIE_SECURE=true`。
3. 首次注册的账号自动成为管理员。登录后进入 `/admin/settings`，可切换 Mock/百炼并保存 API Key、模型、音色和服务地址；密钥写入持久化的 `/app/data/config/ai.env`，不会返回浏览器。
4. 运行 `docker compose up -d --build`。
5. 管理员可在配置页确认教材版权后，一键同步固定 `v1.1.0-assets` 的五个资源包。下载包保存在 `resource_assets` 卷，派生 WebP 保存在 `textbook_pages` 卷；两者都不得通过 Caddy 公开。
6. 定时执行 `deploy/backup.ps1` 或使用等价 Linux 备份。脚本备份 SQLite 和运行时 AI 配置；大体积、已校验的 Release 包可按需重新下载，也可另行做卷快照。

生产环境必须确认课本扫描页的合法展示权。删除相关 `TextbookEdition` 数据和卷内目录即可下架。
