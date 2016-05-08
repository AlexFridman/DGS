import logging
import time
from threading import Thread, Condition

import mongoengine as me
from celery.task.control import discard_all

from dgs.gsserver.conf import conf
from dgs.gsserver.db.gstask import GSTask, TaskState
from dgs.gsserver.errors import TaskNotFoundError

logging.basicConfig(level=logging.DEBUG)


class TaskController(Thread):
    cfg = conf.TaskController

    def __init__(self):
        super().__init__()
        self._running = False
        self._task_add_condition = Condition()

    def _raise_task_add_event(self):
        self._task_add_condition.acquire()
        self._task_add_condition.notify()
        self._task_add_condition.release()

    def _wait_for_task_add_event(self):
        self._task_add_condition.acquire()
        self._task_add_condition.wait()
        self._task_add_condition.release()

    def add_task(self, task):
        # TODO: think about mutual exclusion with task updation
        task.delay()
        task.save()
        self._raise_task_add_event()

    @staticmethod
    def get_tasks(sort='date', state=None, q='', offset=0, count=50):
        tasks = GSTask.objects(title__icontains=q).order_by('-start_time')
        if state and state != 'all':
            tasks = tasks.filter(state__iexact=state)
        total = tasks.clone().count()
        if sort != 'date':
            tasks = tasks
        tasks = tasks.skip(offset).limit(count)
        return total, [task.to_json() for task in tasks]

    @staticmethod
    def cancel_task(task_id):
        task = GSTask.get_by_id(task_id)
        if task:
            task.cancel()
        else:
            raise TaskNotFoundError(task_id)

    @staticmethod
    def cancel_all_tasks():
        discard_all()

    @staticmethod
    def _update(tasks):
        for task in tasks:
            task.update_state()

    @staticmethod
    def _get_tasks_to_update():
        return GSTask.objects(
            me.Q(state__ne=TaskState.FAILED) & me.Q(state__ne=TaskState.CANCELED) & me.Q(state__ne=TaskState.SUCCESS))

    def run(self):
        self._running = True
        while self._running:
            tasks_to_update = self._get_tasks_to_update()
            logging.debug('Found {} task(s) to update'.format(len(tasks_to_update)))
            if tasks_to_update:
                self._update(tasks_to_update)
                time.sleep(self.cfg.tick_interval)
            elif self.cfg.wait_task_add_event:
                logging.debug('Waiting an event')
                self._wait_for_task_add_event()
            else:
                time.sleep(self.cfg.tick_interval)
