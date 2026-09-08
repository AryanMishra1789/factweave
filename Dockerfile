FROM python:3.11-slim
WORKDIR /app
COPY app ./app
COPY pyproject.toml .
RUN pip install --no-cache-dir .
ENV DATABASE_URL=postgresql+psycopg://factweave:factweave@db:5432/factweave
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app.main:app"]
