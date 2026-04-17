FROM python:3.12-slim

WORKDIR /app

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/static ./static
COPY app/templates ./templates
COPY app/main.py .

RUN mkdir -p /app/data

ENV DB_PATH=/app/data/finance.db
ENV STATIC_DIR=/app/static
ENV TEMPLATES_DIR=/app/templates

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
