import time
from threading import Thread, Condition, Lock

from dgs.gsserver.db.gsresource import GSResource
from dgs.gsserver.errors import ResourceNotFoundError, ResourceUnavailableError


class ResourceController(Thread):
    tick_interval = 1

    def __init__(self):
        super().__init__()
        self._running = False
        self._resource_delete_request_condition = Condition()
        self._resource_locking_lock = Lock()

    def _raise_resource_delete_event(self):
        self._resource_delete_request_condition.acquire()
        self._resource_delete_request_condition.notify()
        self._resource_delete_request_condition.release()

    def _wait_for_resource_delete_event(self):
        self._resource_delete_request_condition.acquire()
        self._resource_delete_request_condition.wait()
        self._resource_delete_request_condition.release()

    @staticmethod
    def add_resource(resource):
        resource.save()

    @staticmethod
    def schedule_resource_deletion(resource_id):
        resource = GSResource.objects.get(resource_id=resource_id)
        if resource:
            resource.is_deletion_requested = True
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

    def run(self):
        self._running = True
        while self._running:
            with self._resource_locking_lock:
                resource_to_delete_count = GSResource.objects(is_deletion_requested=True).count()
                if resource_to_delete_count:
                    for resource in GSResource.objects(is_deletion_requested=True, is_locked=False):
                        resource.delete()
                    time.sleep(self.tick_interval)
            if not resource_to_delete_count:
                self._wait_for_resource_delete_event()
