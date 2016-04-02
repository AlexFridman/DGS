import logging

from flask import Flask

from src.gsserver.celeryapp import init_celery_app
from src.gsserver.conf import conf
from src.gsserver.db import init_mongodb

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
