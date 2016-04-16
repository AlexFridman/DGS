import mongoengine as me

from dgs.gsserver.errors import ResourceUnavailableError


class GSResource(me.Document):
    resource_id = me.StringField(primary_key=True)
    name = me.StringField()
    content = me.BinaryField()
    is_deletion_requested = me.BooleanField()
    lockers = me.ListField()

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

    @property
    def is_locked(self):
        return len(self.lockers) > 0

    @classmethod
    def lock_resources(cls, locker_id, resource_ids):
        if cls.is_resources_available(resource_ids):
            for resource_id in resource_ids:
                resource = cls.get_by_id(resource_id)
                if locker_id not in resource.lockers:
                    resource.lockers.append(locker_id)
                    resource.save()
        else:
            raise ResourceUnavailableError()

    @classmethod
    def unlock_resources(cls, locker_id, resource_ids):
        if cls.is_resources_available(resource_ids):
            for resource_id in resource_ids:
                resource = cls.get_by_id(resource_id)
                try:
                    resource.lockers.remove(locker_id)
                except ValueError:
                    pass
                else:
                    resource.save()
        else:
            raise ResourceUnavailableError()
