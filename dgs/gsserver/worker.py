from dgs.gsserver.celeryapp import app
from dgs.gsserver.celeryapp import init_celery_app
from dgs.gsserver.conf import conf
from dgs.gsserver.db import init_mongodb


def run_worker():
    init_mongodb(conf.Mongo.connection)
    init_celery_app(conf.Celery.conf)

    app.worker_main([
        'worker',
        '--loglevel=info',
    ])


def entry_point():
    run_worker()


if __name__ == '__main__':
    entry_point()
