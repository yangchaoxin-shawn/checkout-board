# 作战打卡看板 · 后端 API 镜像（纯 API，无静态文件）
FROM python:3.13-slim

WORKDIR /app
COPY *.py ./
RUN mkdir -p /app/data

ENV HOST=0.0.0.0 \
    PORT=8080 \
    CHECKIN_PASSWORD=365 \
    CHECKIN_SECRET=change-me-in-production

EXPOSE 8080
CMD ["python3", "-u", "main.py", "--host", "0.0.0.0", "--port", "8080", "--api-only"]
