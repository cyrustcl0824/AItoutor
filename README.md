# AI Primary Tutor

面向中国小学三至六年级学生的英语 AI 家教。Next.js Web/PWA 复用固定版本的 ChinaTextbookStudyFree Core 和英语学习体验，FastAPI/SQLite 是学习状态唯一来源，M5Stack 使用同一套 API。

## 本地启动（Mock AI）

```powershell
python -m venv .venv
.venv\Scripts\pip install -r backend\requirements.txt
Copy-Item .env.example .env
.venv\Scripts\python backend\scripts\migrate.py
.venv\Scripts\uvicorn app.main:app --app-dir backend --reload
```

前端需要 Node.js 22 LTS：

```powershell
npm install
npm --workspace ai-tutor-web run dev
```

打开 `http://localhost:3000`。空数据库中第一个注册账号是管理员；现有数据库升级时，最早创建的账号会迁移为管理员。管理员登录后可在底部“配置”或 `/admin/settings` 中配置百炼、测试 Chat → TTS → ASR，并同步教材资源。

AI 老师页保留文字聊天，并提供“开始语音对话”。用户主动授权麦克风后，浏览器会在约 1.2 秒静音时自动提交当前一句，服务端一次完成 ASR → Tutor → TTS，再自动恢复监听。

API 文档位于 `http://localhost:8000/docs`。生产部署说明见 `deploy/README.md`。

## 教材资产

`curriculum/import_textbooks.py` 可重复导入固定 commit 的教材清单、题目/解析、课文、故事和课本原页。无原页 Release 时也可仅导入仓库内题库：

```powershell
.venv\Scripts\python curriculum\import_textbooks.py --upstream C:\path\to\ChinaTextbookStudyFree
```

课本资源不会提交到 Git，也不会打入容器镜像。部署者必须确认拥有展示教材页面的合法权利。上游来源与许可见 `packages/core/NOTICE.md`、`frontend/UPSTREAM_NOTICE.md` 和 `skills/vendor/hermes/NOTICE.md`。
