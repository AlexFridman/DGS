import uuid

import mongoengine as me

from dgs.gsserver.errors import ResourceUnavailableError


class GSResource(me.Document):
    resource_id = me.StringField(primary_key=True)
    title = me.StringField(default=resource_id)
    content = me.BinaryField()
    is_deletion_requested = me.BooleanField(default=False)
    lockers = me.ListField()
    size = me.IntField()

    @classmethod
    def create(cls, content, name=None):
        resource_id = str(uuid.uuid4())
        name = name or resource_id
        return cls(resource_id=resource_id, name=name, content=content, size=len(content))

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
        return bool(self.lockers)

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

    def to_json(self):
        return {'resource_id': self.resource_id, 'title': self.title,
                'size': self.size, 'is_locked': self.is_locked,
                'lockers': self.lockers, 'is_deletion_requested': self.is_deletion_requested}
