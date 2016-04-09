import logging

from flask import Flask

from dgs.gsserver.celeryapp import init_celery_app
from dgs.gsserver.conf import conf
from dgs.gsserver.db import init_mongodb

app = Flask(__name__)


def run_master():
    init_celery_app(conf.Celery.conf)
    init_mongodb(conf.Mongo.connection)

    try:
        app.run(host=conf.Master.host, port=conf.Master.port, use_reloader=False, threaded=True)
    except:
        logging.exception('error while starting flask server, shutting down')


def entry_point():
    run_master()


if __name__ == '__main__':
    entry_point()
