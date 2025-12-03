import os
import multiprocessing

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
wsgi_app = "surveillance_system.asgi:application"
loglevel = "info"
accesslog = "-"
errorlog = "-"
timeout = 300  # 5 minutes pour les uploads de fichiers volumineux
preload_app = True
limit_request_line = 8190  # Augmenter la limite de ligne de requête
limit_request_fields = 10000  # Augmenter le nombre de champs 