import pymongo


class Mongo:
    read_preference = pymongo.ReadPreference.PRIMARY

    def __init__(self, db, host, username=None, password=None):
        self.db = db
        self.username = username
        self.password = password

        self.host = 'mongodb://{}:{}@{}/{}'.format(username, password, host, db)

        self.celery_broker_db = db
        self.celery_backend_db = db

        self.connection = {
            'host': self.host,
            'read_preference': self.read_preference,
        }


class Celery:
    def __init__(self, mongo_conf):
        self.conf = {
            'BROKER_URL': mongo_conf.host,

            'CELERY_RESULT_BACKEND': 'mongodb',
            'CELERY_MONGODB_BACKEND_SETTINGS': {
                'host': mongo_conf.host,
                'database': mongo_conf.db,
                'taskmeta_collection': 'taskmeta_collection'
            },
            'CELERY_SEND_EVENTS': True,
            'CELERY_SEND_TASK_SENT_EVENT': True,
            'CELERY_DISABLE_RATE_LIMITS': True
        }


class Master:
    def __init__(self, host, port):
        self.host = host
        self.port = port


class GSServerConf:
    def __init__(self, mongo, celery, master):
        self.Mongo = mongo
        self.Celery = celery
        self.Master = master
