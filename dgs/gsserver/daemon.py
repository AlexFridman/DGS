import logging

import chardet
from flask import Flask
from flask import render_template
from flask import request
from flask.ext.responses import json_response

from src.gsserver.celeryapp import init_celery_app
from src.gsserver.conf import conf
from src.gsserver.db import init_mongodb
from src.gsserver.db.gstask import GSTask, ScriptParseError
from src.gsserver.task_controller import TaskController
from src.gsserver.task_controller import TaskNotFoundError

app = Flask(__name__)
controller = TaskController()


def run_master():
    init_celery_app(conf.Celery.conf)
    init_mongodb(conf.Mongo.connection)

    try:
        app.run(host=conf.Master.host, port=conf.Master.port, use_reloader=False, threaded=True)
    except:
        logging.exception('error while starting flask server, shutting down')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/cancel/<task_id>')
def cancel(task_id):
    try:
        TaskController.cancel_task(task_id)
    except TaskNotFoundError as e:
        return json_response({'message': 'task not found'}, status_code=400)
    else:
        return json_response({'message': 'ok'}, status_code=200)


@app.route('/add', methods=['POST'])
def add():
    try:
        data = request.data
        encoding = chardet.detect(data)
        print(encoding)
        if not encoding:
            return json_response({'message': 'Invalid encoding'}, status_code=400)
        data = data.decode(encoding['encoding'])
        task = GSTask.create_from_script(data)
    except ScriptParseError as e:
        return json_response({'message': e.script_errors}, status_code=400)
    else:
        controller.add_task(task)
        return json_response({'message': 'ok'}, status_code=200)


@app.route('/info')
def info():
    return json_response({'tasks': TaskController.get_tasks()}, status_code=200)


def entry_point():
    run_master()


if __name__ == '__main__':
    entry_point()
    controller.start()
