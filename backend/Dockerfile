# ===== 生产环境 Dockerfile（支持 100 人并发） =====
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ENV PIP_INDEX_URL=${PIP_INDEX_URL} \
    PIP_DEFAULT_TIMEOUT=300 \
    PIP_RETRIES=10 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

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

# 使用 gunicorn + eventlet 运行（支持 WebSocket）
CMD ["gunicorn", "-k", "eventlet", "-w", "1", "--threads", "50", \
     "--bind", "0.0.0.0:5000", "--timeout", "120", \
     "--access-logfile", "-", "--error-logfile", "-", \
     "run:app"]
