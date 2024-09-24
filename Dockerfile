FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0


WORKDIR /app


COPY . /app


RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

    CMD ["celery", "-A", "app.celery.celery_app", "worker", "--loglevel=info", "--concurrency=4", "-Q", "main-queue"]

