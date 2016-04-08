import datetime
import sys
import traceback
import uuid

import mongoengine as me
from pyext import RuntimeModule
from sklearn.cross_validation import cross_val_score
from sklearn.grid_search import ParameterGrid

from src.gsserver.celeryapp import run_subtask


class TaskState:
    IDLE = 'IDLE'
    RUNNING = 'RUNNING'
    FAILED = 'FAILED'
    SUCCESS = 'SUCCESS'
    CANCELED = 'CANCELED'


class GSSubtask(me.Document):
    subtask_id = me.StringField(primary_key=True)
    celery_task_id = me.StringField()
    parent_task_id = me.StringField()
    start_time = me.DateTimeField()
    end_time = me.DateTimeField()
    params = me.DictField()
    score = me.FloatField()
    state = me.StringField()
    stack_trace = me.DictField()

    @property
    def parent_task(self):
        return GSTask.objects.get(task_id=self.parent_task_id)

    def _get_script(self):
        return self.parent_task.script

    def execute(self):
        if self.state == TaskState.CANCELED:
            return
        if self.parent_task.state == TaskState.CANCELED:
            return
        success = False
        self.state = TaskState.RUNNING
        self.start_time = datetime.datetime.now()
        self.save()
        script = self._get_script()
        module = RuntimeModule.from_string('module', '', script)
        try:
            self.score = cross_val_score(module.Estimator(**self.params), X=module.X, y=module.y,
                                         scoring=vars(module).get('scoring')).mean()
            success = True
        except Exception as e:
            ex_type, ex, tb = sys.exc_info()
            self.stack_trace = {
                'ex_type': str(ex_type),
                'ex_message': ex,
                'traceback': ''.join(traceback.format_tb(tb)[4:])
            }
        finally:
            if success:
                self.state = TaskState.SUCCESS
                self.end_time = datetime.datetime.now()
            else:
                self.state = TaskState.FAILED
            self.save()


class GSTask(me.Document):
    task_id = me.StringField(primary_key=True)
    subtasks = me.ListField(me.ReferenceField(GSSubtask, reverse_delete_rule=me.NULLIFY))
    state = me.StringField()
    script = me.StringField()
    start_time = me.DateTimeField()
    end_time = me.DateTimeField()
    actualize_date = me.DateTimeField()
    n_subtasks = me.IntField()
    n_completed = me.IntField()
    best_score = me.FloatField()
    best_params = me.DictField()
    param_errors = me.DictField()
    note = me.StringField()

    def __custom__init__(self, param_grid, script):
        task_id = str(uuid.uuid4())
        subtasks = [
            GSSubtask(subtask_id=str(uuid.uuid4()), state=TaskState.IDLE, params=param_comb, parent_task_id=task_id) for
            param_comb in ParameterGrid(param_grid)]
        GSSubtask.objects.insert(subtasks)
        super().__init__(task_id=task_id, script=script, subtasks=subtasks, n_subtasks=len(subtasks))
        return self

    @classmethod
    def create(cls, param_grid, script):
        return cls().__custom__init__(param_grid, script)

    def update_state(self):
        if not self.state == TaskState.CANCELED:
            states = [subtask.state for subtask in self.subtasks if subtask.state is not None]
            if TaskState.FAILED in states:
                self.state = TaskState.FAILED
            elif TaskState.IDLE in states:
                self.state = TaskState.IDLE
            elif TaskState.RUNNING in states:
                self.state = TaskState.RUNNING
            else:
                self.state = TaskState.SUCCESS

        self.n_completed = sum(1 for state in states if state == TaskState.SUCCESS)

        start_times = [subtask.start_time for subtask in self.subtasks if subtask.state != TaskState.IDLE]
        if start_times:
            self.start_time = min(start_times)

        end_times = [subtask.end_time for subtask in self.subtasks if subtask.state == TaskState.SUCCESS]
        if end_times:
            self.end_time = max(end_times)

        self.actualize_date = datetime.datetime.now()

        scores = [subtask.score for subtask in self.subtasks if subtask.state == TaskState.SUCCESS]
        if scores:
            self.best_score = max(scores)
            self.best_params = [subtask.params for subtask in self.subtasks if subtask.score == self.best_score][0]

        self.save()

    def set_param_errors(self, errors):
        self.param_errors = errors
        self.save()

    def cancel_task(self):
        self.state = TaskState.CANCELED
        self.save()

    def delay(self):
        self.state = TaskState.RUNNING
        self.save()

        for subtask in self.subtasks:
            result = run_subtask.delay(subtask.subtask_id)
            subtask.celery_task_id = result.id
            subtask.save()
