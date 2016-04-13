import logging
import time
from threading import Thread, Condition

from celery.task.control import discard_all

from dgs.gsserver.db.gstask import GSTask, TaskState

logging.basicConfig(level=logging.DEBUG)


class TaskNotFoundError(Exception):
    def __init__(self, task_id):
        self.task_id = task_id


class TaskController(Thread):
    tick_interval = 1

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
    def get_tasks(sort, status, q, offset, count):
        tasks = GSTask.objects(title__icontains=q)
        if status:
            tasks = tasks.filter(status__iexact=status)
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
    def _get_running_tasks():
        return GSTask.objects(state=TaskState.RUNNING)

    def run(self):
        self._running = True
        while self._running:
            running_tasks = self._get_running_tasks()
            logging.debug('Found {} running task(s)'.format(len(running_tasks)))
            if running_tasks:
                self._update(running_tasks)
                time.sleep(self.tick_interval)
            else:
                logging.debug('Waiting an event')
                self._wait_for_task_add_event()
