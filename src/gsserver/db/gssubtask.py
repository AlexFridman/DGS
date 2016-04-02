import mongoengine as me


class GSSubTask(me.Document):
    subtask_id = me.UUIDField(primary_key=True)
    start_time = me.DateTimeField()
    end_time = me.DateTimeField()
    params = me.DictField()
    score = me.FloatField()
    state = me.StringField()
    stack_trace = me.StringField()
