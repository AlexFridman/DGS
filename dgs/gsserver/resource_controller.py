import time
from threading import Thread, Condition, Lock

from dgs.gsserver.db.gsresource import GSResource
from dgs.gsserver.errors import ResourceNotFoundError, ResourceUnavailableError


class ResourceController(Thread):
    tick_interval = 1

    def __init__(self):
        super().__init__()
        self._running = False
        self._resource_add_request_condition = Condition()
        self._resource_locking_lock = Lock()

    def _raise_resource_add_event(self):
        self._resource_add_request_condition.acquire()
        self._resource_add_request_condition.notify()
        self._resource_add_request_condition.release()

    def _wait_for_resource_add_event(self):
        self._resource_add_request_condition.acquire()
        self._resource_add_request_condition.wait()
        self._resource_add_request_condition.release()

    def add_resource(self, resource):
        resource.save()
        self._raise_resource_add_event()

    @staticmethod
    def schedule_resource_deletion(resource_id):
        resource = GSResource.objects.get(resource_id=resource_id)
        if resource:
            resource.is_deletion_requested = True
            resource.save()
        else:
            raise ResourceNotFoundError(resource_id)

    def lock_resources(self, locker_id, resource_ids):
        if not resource_ids:
            return
        with self._resource_locking_lock:
            if GSResource.is_resources_available(resource_ids):
                for resource_id in resource_ids:
                    resource = GSResource.get_by_id(resource_id)
                    if locker_id not in resource.lockers:
                        resource.lockers.append(locker_id)
                        resource.save()
            else:
                raise ResourceUnavailableError()

    @staticmethod
    def get_resources(q='', is_locked=None, offset=0, count=50, include_content=True):
        resources = GSResource.objects(title__icontains=q)
        if is_locked is not None:
            resources = resources.filter(lockers__0__exists=is_locked)
        if not include_content:
            resources = resources.exclude('content')
        total = resources.clone().count()
        resources = resources.skip(offset).limit(count)
        return total, [resource.to_json() for resource in resources]

    @staticmethod
    def update_locker_list(resource):
        from dgs.gsserver.db.gstask import GSTask
        nonlockers = []
        for locker_id in resource.lockers:
            if not GSTask.get_by_id(locker_id):
                nonlockers.append(locker_id)

        if nonlockers:
            resource.lockers = list(set(resource.lockers).difference(nonlockers))
            resource.save()

    def run(self):
        self._running = True
        while self._running:
            with self._resource_locking_lock:
                for resource in GSResource.objects(lockers__0__exists=True):
                    self.update_locker_list(resource)

                for resource in GSResource.objects(is_deletion_requested=True, lockers__0__exists=False):
                    resource.delete()

            if GSResource.objects.count():
                time.sleep(self.tick_interval)
            else:
                self._wait_for_resource_add_event()
