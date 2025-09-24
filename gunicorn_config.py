import os
import multiprocessing

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
wsgi_app = "surveillance_system.asgi:application"
loglevel = "info"
accesslog = "-"
errorlog = "-"
timeout = 120
preload_app = True 