# 确保应用启动时Celery也被加载
from .celery_app import app as celery_app

__all__ = ('celery_app',) 