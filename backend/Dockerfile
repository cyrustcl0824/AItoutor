FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/alembic.ini .
COPY backend/alembic ./alembic
COPY backend/app ./app
COPY backend/scripts ./scripts
COPY skills ./skills
CMD ["sh", "-c", "python scripts/migrate.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
