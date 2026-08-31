# AI Primary Tutor

面向中国小学三至六年级学生的英语 AI 家教 V1。Web/PWA 是主客户端，M5Stack 使用同一套 API。

## 本地启动（Mock AI）

```powershell
python -m venv .venv
.venv\Scripts\pip install -r backend\requirements.txt
Copy-Item .env.example .env
.venv\Scripts\uvicorn app.main:app --app-dir backend --reload
```

前端需要 Node.js 22 LTS：

```powershell
cd frontend
npm install
npm run dev
```

API 文档位于 `http://localhost:8000/docs`。生产部署说明见 `deploy/README.md`。

## 教材资产

`curriculum/import_textbooks.py` 可重复导入教材清单、课文句子及课本原页。课本资源不会提交到 Git，也不会打入容器镜像。部署者必须确认拥有展示教材页面的合法权利。

