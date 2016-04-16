import mongoengine as me


class GSResource(me.Document):
    resource_id = me.StringField(primary_key=True)
    name = me.StringField()
    content = me.BinaryField()
    is_locked = me.BooleanField(default=False)
    is_deletion_requested = me.BooleanField()

    @classmethod
    def get_by_id(cls, resource_id):
        try:
            return GSResource.objects.get(resource_id=resource_id)
        except me.DoesNotExist:
            pass

    @classmethod
    def is_resources_available(cls, resource_ids):
        for resource_id in resource_ids:
            resource = cls.get_by_id(resource_id)
            if not resource or resource.is_deletion_requested:
                return False
        return True
