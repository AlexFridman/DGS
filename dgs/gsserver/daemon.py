import logging
import re
import uuid
from json.decoder import JSONDecodeError

from flask import Flask
from flask import request
from flask.ext.cors import cross_origin
from flask.ext.responses import json_response

from dgs.gsserver.celeryapp import init_celery_app
from dgs.gsserver.conf import conf
from dgs.gsserver.db import init_mongodb
from dgs.gsserver.db.gsresource import GSResource
from dgs.gsserver.db.gstask import GSTask, TaskState
from dgs.gsserver.errors import ScriptParseError, ResourceUnavailableError, SearchRequestError, TaskStateError, \
    ResourceNotFoundError
from dgs.gsserver.resource_controller import ResourceController
from dgs.gsserver.task_controller import TaskController
from dgs.gsserver.task_controller import TaskNotFoundError

app = Flask(__name__)
task_controller = TaskController()
resource_controller = ResourceController()


@app.route('/cancel/<task_id>')
@cross_origin()
def cancel(task_id):
    try:
        TaskController.cancel_task(task_id)
    except TaskNotFoundError as e:
        return json_response({'message': 'task not found'}, status_code=400)
    except TaskStateError as e:
        return json_response({'message': e.message}, status_code=400)
    else:
        return json_response({'message': 'ok'})


@app.route('/cancel_all')
@cross_origin()
def cancel_all():
    task_controller.cancel_all_tasks()
    return json_response({'message': 'ok'})


@app.route('/add_task', methods=['POST'])
@cross_origin()
def add_task():
    temp_locker = uuid.uuid4()
    resource_ids = None
    try:
        args = request.json

        resources = args.get('resources', {})
        resource_ids = resources.values()
        title = args.get('title', '')
        script = args.get('file', '')
        # TODO: probably, should be moved elsewhere
        resource_controller.lock_resources(temp_locker, resource_ids)
        task = GSTask.create_from_script(script, resources, title=title, task_id=str(temp_locker))
        is_successfully_created = True
    except ScriptParseError as e:
        return json_response({'message': e.script_errors}, status_code=400)
    except ResourceUnavailableError as e:
        return json_response({'message': 'Some resources are unavailable'}, status_code=400)
    except JSONDecodeError as e:
        return json_response({'message': 'Data is not in json format'}, status_code=400)
    else:
        task_controller.add_task(task)
        return json_response({'message': 'ok'})
    finally:
        if resource_ids and not is_successfully_created:
            GSResource.unlock_resources(temp_locker, resource_ids)


def validate_search_params(raw_params, config):
    errors = {}
    params = {}

    for name, (default_value, validator, transformer, validation_error_message) in config.items():
        raw_value = raw_params.get(name, default_value)
        if validator and not validator(raw_value):
            errors[name] = validation_error_message
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


@app.route('/task_info')
@cross_origin()
def task_info():
    config = {
        'sort': ('date', None, None, None),
        'q': ('', None, None, None),
        'state': ('ALL', lambda x: x.upper() in list(vars(TaskState)) + ['ALL'], lambda x: x.upper(), 'No such state'),
        'offset': ('0', lambda x: re.match(r'\d+', x), lambda x: int(x), None),
        'count': ('50', lambda x: re.match(r'\d+', x), lambda x: int(x), None)
    }

    try:
        params = validate_search_params(request.args, config)
    except SearchRequestError as e:
        return json_response({'errors': e.errors})
    else:
        total, items = task_controller.get_tasks(**params)
        return json_response({'tasks': {'count': total, 'items': items}})


@app.route('/add_resource', methods=['POST'])
@cross_origin()
def add_resource():
    args = request.json

    if 'file' not in args or not isinstance(args['file'], str) or not args['file']:
        return json_response({'message': 'can not add an empty resource'}, status_code=400)

    resource = GSResource.create(args['file'].encode('utf8'), args.get('title'))
    try:
        resource_controller.add_resource(resource)
    except Exception as e:
        return json_response({'message': str(e)}, status_code=400)
    else:
        return json_response({'message': 'ok'})


@app.route('/resource_info')
@cross_origin()
def resource_info():
    config = {
        'q': ('', None, None, None),
        'is_locked': ('',
                      lambda x: x.lower() in ('true', 'false', 'all', ''),
                      lambda x: {'true': True, 'false': False}.get(x.lower()),
                      'No such state'),
        'offset': ('0', lambda x: re.match(r'\d+', x), lambda x: int(x), None),
        'count': ('50', lambda x: re.match(r'\d+', x), lambda x: int(x), None)
    }
    try:
        params = validate_search_params(request.args, config)
    except SearchRequestError as e:
        return json_response({'errors': e.errors})
    else:
        total, items = resource_controller.get_resources(include_content=False, **params)
        return json_response({'resources': {'count': total, 'items': items}})


@app.route('/delete_resource/<resource_id>')
@cross_origin()
def delete_resource(resource_id):
    try:
        resource_controller.schedule_resource_deletion(resource_id)
    except ResourceNotFoundError:
        return json_response({'message': 'resource not found'}, status_code=400)
    else:
        return json_response({'message': 'ok'})


def run_master():
    init_celery_app(conf.Celery.conf)
    init_mongodb(conf.Mongo.connection)
    task_controller.start()

    try:
        app.run(host=conf.Master.host, port=conf.Master.port, use_reloader=False, threaded=True)
    except:
        logging.exception('error while starting flask server, shutting down')


def entry_point():
    run_master()


if __name__ == '__main__':
    entry_point()
