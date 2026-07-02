
import os
from datetime import datetime, timezone
from celery import Celery
from celery.schedules import crontab

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
app = Celery("leadhunter", broker=redis_url, backend=redis_url)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Sao_Paulo",
    enable_utc=True,
)

# P2-03: Job automático apenas se ENABLE_DAILY_PIPELINE=true
if os.getenv("ENABLE_DAILY_PIPELINE", "false").lower() == "true":
    app.conf.beat_schedule = {
        "daily-pipeline": {
            "task": "leadhunter_worker.tasks.pipeline.run_pipeline",
            "schedule": crontab(hour=9, minute=0),
            "args": ("clínicas odontológicas", "Belo Horizonte, MG", 100),
        },
    }
