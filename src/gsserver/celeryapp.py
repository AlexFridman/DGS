from multiprocessing import current_process

from celery import Celery
from celery.signals import worker_process_init


@worker_process_init.connect
def fix_multiprocessing(**kwargs):
    if not hasattr(current_process(), '_config'):
        current_process()._config = {'semprefix': '/mp'}


app = Celery()

app.conf.update(
    CELERY_TRACK_STARTED=True,
    CELERY_ACKS_LATE=True,
    CELERYD_PREFETCH_MULTIPLIER=1,
)


def init_celery_app(conf):
    app.conf.update(**conf)
    return app


@app.task
def run_subtask(id):
    from src.gsserver.db.gstask import GSSubtask
    subtask = GSSubtask.objects.get(subtask_id=id)
    subtask.execute()
