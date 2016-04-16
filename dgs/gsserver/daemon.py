import logging
import re

import chardet
from flask import Flask
from flask import request
from flask.ext.cors import cross_origin
from flask.ext.responses import json_response

from dgs.gsserver.celeryapp import init_celery_app
from dgs.gsserver.conf import conf
from dgs.gsserver.db import init_mongodb
from dgs.gsserver.db.gstask import GSTask, ScriptParseError, TaskState
from dgs.gsserver.task_controller import TaskController
from dgs.gsserver.task_controller import TaskNotFoundError

app = Flask(__name__)
controller = TaskController()


@app.route('/cancel/<task_id>')
@cross_origin()
def cancel(task_id):
    try:
        TaskController.cancel_task(task_id)
    except TaskNotFoundError as e:
        return json_response({'message': 'task not found'}, status_code=400)
    else:
        return json_response({'message': 'ok'}, status_code=200)


@app.route('/cancel_all')
@cross_origin()
def cancel_all():
    controller.cancel_all_tasks()
    return json_response({'message': 'ok'}, status_code=200)


@app.route('/add', methods=['POST'])
@cross_origin()
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


class SearchRequestError(Exception):
    def __init__(self, errors):
        self.errors = errors


def validate_search_params(raw_params):
    params_validators_transformers = {
        'sort': (lambda x: True, None, None),
        'q': (None, None, None),
        'state': (lambda x: x in vars(TaskState), None, 'No such state'),
        'offset': (lambda x: re.match(r'\d+', x), lambda x: int(x), None),
        'count': (lambda x: re.match(r'\d+', x), lambda x: int(x), None)
    }

    errors = {}
    params = {}

    for name, (validator, transformer, validation_error_message) in params_validators_transformers.items():
        raw_value = raw_params[name]
        try:
            if validator:
                validator(raw_value)
        except Exception as e:
            errors[name] = str(e)
        else:
            try:
                value = transformer(raw_value) if transformer else raw_value
            except Exception as e:
                errors[name] = validation_error_message if validation_error_message else str(e)
            else:
                params[name] = value

    if errors:
        raise SearchRequestError(errors)
    return params


@app.route('/info')
@cross_origin()
def info():
    args = request.args
    search_params = {
        'sort': args.get('sort', 'date').lower(),
        'q': args.get('q', ''),
        'state': args.get('state', 'all').lower(),
        'offset': args.get('offset', '0'),
        'count': args.get('count', '50')
    }

    try:
        params = validate_search_params(search_params)
    except SearchRequestError as e:
        return json_response({'errors': e.errors})
    else:
        total, items = TaskController.get_tasks(**params)
        return json_response({'tasks': {'count': total, 'items': items}}, status_code=200)


def run_master():
    init_celery_app(conf.Celery.conf)
    init_mongodb(conf.Mongo.connection)
    controller.start()

    try:
        app.run(host=conf.Master.host, port=conf.Master.port, use_reloader=False, threaded=True)
    except:
        logging.exception('error while starting flask server, shutting down')


@app.route('/add_resource')
@cross_origin()
def add_resource():
    pass


@app.route('/resource_info')
@cross_origin()
def resource_info():
    pass


@app.route('/delete_resource/<resource_id>')
@cross_origin()
def delete_resource(resource_id):
    pass


def entry_point():
    run_master()


if __name__ == '__main__':
    entry_point()
