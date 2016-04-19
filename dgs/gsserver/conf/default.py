from dgs.gsserver.conf.conf import Celery, Mongo, Master, GSServerConf

mongo_conf = {
    'db': 'dgs',
    'hosts': (),
    'username': '',
    'password': '',
    'rs': 'dgs_rs'
}

master_conf = {
    'host': '::',
    'port': 5000
}


class TaskControllerConfig:
    tick_interval = 1
    wait_task_add_event = False


mongo = Mongo(**mongo_conf)
master = Master(**master_conf)
celery = Celery(mongo)

conf = GSServerConf(mongo, celery, master, TaskControllerConfig)
