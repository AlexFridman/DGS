from celery import Celery

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
    from src.gsserver.db.gstask import GSSubtask
    subtask = GSSubtask.objects.get(subtask_id=id)
    subtask.execute()
