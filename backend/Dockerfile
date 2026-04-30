# ===== 生产环境 Dockerfile (支持100人并发) =====
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建上传目录
RUN mkdir -p uploads

# 环境变量
ENV FLASK_ENV=production \
    PYTHONUNBUFFERED=1 \
    GUNICORN_WORKERS=4 \
    GUNICORN_THREADS=50 \
    GUNICORN_TIMEOUT=120 \
    GUNICORN_BIND=0.0.0.0:5000

EXPOSE 5000

# 使用 gunicorn + eventlet 运行（支持WebSocket）
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "4", "--threads", "50", \
     "--bind", "0.0.0.0:5000", "--timeout", "120", \
     "--access-logfile", "-", "--error-logfile", "-", \
     "run:app"]
