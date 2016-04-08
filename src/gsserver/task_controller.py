import time
from threading import Thread, Condition

from src.gsserver.db.gstask import GSTask, TaskState


class TaskController(Thread):
    tick_interval = 1

    def __init__(self):
        super().__init__()
        self._running = False
        self._task_add_condition = Condition()

    def add_task(self, task):
        # TODO: think about mutual exclusion with task updation
        task.run()
        task.save()
        self._task_add_condition.notify()

    @staticmethod
    def cancel_task(task_id):
        task = GSTask.get_by_id(task_id)
        if task:
            task.cancel()

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
            if running_tasks:
                self._update(running_tasks)
                time.sleep(self.tick_interval)
            else:
                self._task_add_condition.acquire()
                self._task_add_condition.wait()
