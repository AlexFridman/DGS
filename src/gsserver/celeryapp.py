from celery import Celery

import src.gsserver.db.gstask

app = Celery()

app.conf.update(
    CELERY_TASK_SERIALIZER='json',
    CELERY_ACCEPT_CONTENT=['json'],
    CELERY_RESULT_SERIALIZER='json',

    CELERY_TRACK_STARTED=True,
    CELERY_ACKS_LATE=True,
    CELERYD_PREFETCH_MULTIPLIER=1,
)


def init_celery_app(conf):
    app.conf.update(**conf)
    return app


@app.task
def run_subtask(id):
    subtask = src.gsserver.db.gstask.GSSubtask.objects.get(subtask_id=id)
    subtask.execute()
