import datetime
import sys
import traceback
import uuid
from types import FunctionType

import mongoengine as me
import numpy as np
from celery import group
from sklearn.base import ClassifierMixin, RegressorMixin
from sklearn.cross_validation import cross_val_score
from sklearn.grid_search import ParameterGrid

from dgs.gsserver.celeryapp import run_subtask
from dgs.gsserver.db.gsresource import GSResource
from dgs.gsserver.errors import ScriptParseError, TaskStateError
from dgs.gsserver.resource_controller import ResourceNotFoundError


class TaskState:
    IDLE = 'IDLE'
    RUNNING = 'RUNNING'
    FAILED = 'FAILED'
    SUCCESS = 'SUCCESS'
    CANCELED = 'CANCELED'
    PENDING = 'PENDING'


task_params = {
    'Estimator': (True, lambda x: issubclass(x, (ClassifierMixin, RegressorMixin)),
                  'Estimator should be subclass of ClassifierMixin or RegressorMixin'),
    'scoring': (False, lambda x: isinstance(x, (str, FunctionType)), 'Scoring should be of type str or function'),
    'X': (True, lambda x: isinstance(x, np.ndarray), 'X should be of type numpy.ndarray'),
    'y': (True, lambda x: isinstance(x, np.ndarray), 'y should be of type numpy.ndarray'),
    'param_grid': (True, lambda x: isinstance(x, dict), 'param_grid should be of type dict'),
}


class GSSubtask(me.Document):
    subtask_id = me.StringField(primary_key=True)
    parent_task_id = me.StringField()
    start_time = me.DateTimeField()
    end_time = me.DateTimeField()
    params = me.DictField()
    score = me.FloatField()
    state = me.StringField()
    error_info = me.DictField()

    @classmethod
    def get_by_id(cls, subtask_id):
        try:
            return GSSubtask.objects.get(subtask_id=subtask_id)
        except me.DoesNotExist:
            pass

    @property
    def parent_task(self):
        return GSTask.get_by_id(self.parent_task_id)

    def _get_script(self):
        return self.parent_task.script

    def execute(self):
        if self.state == TaskState.CANCELED:
            return
        if self.parent_task.state in (TaskState.CANCELED, TaskState.FAILED):
            return
        success = False
        self.state = TaskState.RUNNING
        self.start_time = datetime.datetime.utcnow()
        self.save()
        script = self._get_script()
        resources = self.parent_task.get_resources()
        module_globals = {'resources': resources}
        try:
            exec(script, {}, module_globals)
            self.score = cross_val_score(module_globals['Estimator'](**self.params), X=module_globals['X'],
                                         y=module_globals['y'],
                                         scoring=module_globals.get('scoring')).mean()
            success = True
        except Exception as e:
            ex_type, ex, tb = sys.exc_info()
            self.error_info = {
                'ex_type': str(ex_type),
                'ex_message': str(ex),
                'traceback': ''.join(traceback.format_tb(tb))
            }
        finally:
            if success:
                self.state = TaskState.SUCCESS
                self.end_time = datetime.datetime.utcnow()
            else:
                self.state = TaskState.FAILED
            self.save()


class GSTask(me.Document):
    task_id = me.StringField(primary_key=True)
    title = me.StringField()
    resources = me.DictField()
    state = me.StringField()
    script = me.StringField()
    start_time = me.DateTimeField()
    end_time = me.DateTimeField()
    actualize_date = me.DateTimeField()
    n_subtasks = me.IntField()
    n_completed = me.IntField(default=0)
    best_score = me.FloatField()
    best_params = me.DictField()
    param_errors = me.DictField()
    note = me.StringField()
    runtime_errors = me.ListField()

    def __custom__init__(self, param_grid, script, resources=None, title='', task_id=None):
        resources = resources or {}
        task_id = task_id or str(uuid.uuid4())
        GSResource.lock_resources(task_id, resources.values())
        subtasks = [
            GSSubtask(subtask_id=str(uuid.uuid4()), state=TaskState.IDLE, params=param_comb, parent_task_id=task_id) for
            param_comb in ParameterGrid(param_grid)]
        GSSubtask.objects.insert(subtasks)
        super().__init__(task_id=task_id, title=title, script=script, n_subtasks=len(subtasks),
                         resources=resources)
        return self

    @classmethod
    def create(cls, param_grid, script, resources=None, title='', task_id=None):
        return cls().__custom__init__(param_grid, script, resources, title=title, task_id=task_id)

    # TODO: test it
    @classmethod
    def create_from_script(cls, code, resources=None, title='', task_id=None):
        script_errors = {}
        try:
            resource_contents = cls._get_resources(resources or {})
            module_globals = {'resources': resource_contents}
            exec(code, {}, module_globals)
        except ResourceNotFoundError:
            raise
        except Exception as e:
            ex_type, ex, tb = sys.exc_info()
            script_errors['script'] = {
                'ex_type': str(ex_type),
                'ex_message': str(ex),
                'traceback': ''.join(traceback.format_tb(tb))
            }
            raise ScriptParseError(script_errors)
        else:
            for param_name, (required, check_func, error_msg) in task_params.items():
                param_in_module = param_name in module_globals
                if not param_in_module and required:
                    script_errors[param_name] = {
                        'ex_message': 'There is no {} in script'.format(param_name)
                    }
                elif param_in_module:
                    try:
                        if not check_func(module_globals[param_name]):
                            script_errors[param_name] = {
                                'ex_message': error_msg
                            }
                    except Exception as e:
                        ex_type, ex, tb = sys.exc_info()
                        script_errors[param_name] = {
                            'ex_type': str(ex_type),
                            'ex_message': str(ex),
                            'traceback': ''.join(traceback.format_tb(tb))
                        }

            if script_errors:
                raise ScriptParseError(script_errors)

            return GSTask.create(module_globals['param_grid'], code, resources, title=title, task_id=task_id)

    def get_resources(self):
        return self._get_resources(self.resources)

    @staticmethod
    def _get_resources(resources):
        result = {}
        for resource_alias, resource_id in resources.items():
            resource = GSResource.get_by_id(resource_id)
            if not resource:
                raise ResourceNotFoundError(resource_id)
            result[resource_alias] = resource.content
        return result

    @classmethod
    def get_by_id(cls, task_id):
        try:
            return GSTask.objects.get(task_id=task_id)
        except me.DoesNotExist:
            pass

    def to_json(self):
        return {'task_id': self.task_id, 'state': self.state, 'start_time': self.start_time,
                'end_time': self.end_time, 'actualize_date': self.actualize_date,
                'n_subtasks': self.n_subtasks, 'n_completed': self.n_completed,
                'best_score': self.best_score, 'best_params': self.best_params,
                'param_errors': self.param_errors, 'title': self.title,
                'runtime_errors': self.runtime_errors}

    def _get_unique_runtime_errors(self):
        unique_errors = {(subtask.error_info['ex_type'],
                          subtask.error_info['ex_message'],
                          subtask.error_info['traceback']) for subtask
                         in self.get_subtasks() if subtask.error_info}
        return [{'ex_type': ex_type, 'ex_message': ex_message, 'traceback': traceback} for
                ex_type, ex_message, traceback in unique_errors]

    def get_subtasks(self):
        return GSSubtask.objects(parent_task_id=self.task_id)

    def update_state(self):
        subtasks = self.get_subtasks()
        subtask_states = [subtask.state for subtask in subtasks if subtask.state is not None]
        unique_subtask_states = set(subtask_states)
        if self.state != TaskState.CANCELED:
            if TaskState.FAILED in unique_subtask_states:
                self.state = TaskState.FAILED
                self.runtime_errors = self._get_unique_runtime_errors()
            elif TaskState.RUNNING in unique_subtask_states or all(
                            state in unique_subtask_states for state in (TaskState.IDLE, TaskState.SUCCESS)):
                self.state = TaskState.RUNNING
            elif all(state == TaskState.SUCCESS for state in unique_subtask_states):
                self.state = TaskState.SUCCESS

        if self.state in (TaskState.FAILED, TaskState.CANCELED, TaskState.SUCCESS):
            GSResource.unlock_resources(self.task_id, self.resources.values())

        self.n_completed = sum(1 for state in subtask_states if state == TaskState.SUCCESS)

        start_times = [subtask.start_time for subtask in subtasks if subtask.start_time is not None]
        if start_times:
            self.start_time = min(start_times)

        end_times = [subtask.end_time for subtask in subtasks if
                     subtask.state == TaskState.SUCCESS and subtask.end_time is not None]
        if end_times:
            self.end_time = max(end_times)

        self.actualize_date = datetime.datetime.now()

        scores = [subtask.score for subtask in subtasks if subtask.state == TaskState.SUCCESS]
        if scores:
            self.best_score = max(scores)
            self.best_params = [subtask.params for subtask in subtasks if subtask.score == self.best_score][0]

        self.save()

    def set_param_errors(self, errors):
        self.param_errors = errors
        self.save()

    def cancel(self):
        if self.state not in (TaskState.IDLE, TaskState.PENDING, TaskState.RUNNING):
            raise TaskStateError('Cannot cancel task with {} state'.format(self.state))
        self.state = TaskState.CANCELED
        GSResource.unlock_resources(self.task_id, self.resources.values())
        self.save()

    def delay(self):
        self.state = TaskState.PENDING
        self.save()
        group(run_subtask.s(subtask.subtask_id) for subtask in self.get_subtasks()).apply_async(compression='zlib')
