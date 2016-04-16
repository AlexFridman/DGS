import mongoengine as me


class GSResource(me.Document):
    resource_id = me.StringField(primary_key=True)
    name = me.StringField()
    content = me.BinaryField()
    is_locked = me.BooleanField(default=False)
    is_deletion_requested = me.BooleanField()
