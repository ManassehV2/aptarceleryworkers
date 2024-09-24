import multiprocessing
from celery import Celery

multiprocessing.set_start_method('fork', force=True)

# Initialize Celery application
celery_app = Celery(
    "detection_tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

# Celery configurations
celery_app.conf.task_routes = {
    "app.worker.detection_tasks": "main-queue",
}
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

import app.ppetask
import app.palletstask
import app.forklifttask


celery_app.autodiscover_tasks(['app.ppetask', 'app.palletstask', 'app.forklifttask'])
