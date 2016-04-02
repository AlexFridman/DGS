import mongoengine as me

from src.gsserver.db.gssubtask import GSSubTask


class TaskState:
    IDLE = 'IDLE'
    RUNNING = 'RUNNING'
    FAILED = 'FAILED'
    SUCCESS = 'SUCCESS'


class GSTask(me.Document):
    task_id = me.UUIDField(primary_key=True)
    subtasks = me.ListField(me.ReferenceField(GSSubTask))
    state = me.StringField()
    start_time = me.DateTimeField()
    end_time = me.DateTimeField()
    actualize_date = me.DateTimeField()
    n_subtasks = me.IntField()
    n_completed = me.IntField()
    best_score = me.FloatField()
    best_params = me.DictField()
    param_errors = me.DictField()
    note = me.StringField()
