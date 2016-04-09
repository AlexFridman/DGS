from dgs.gsserver.conf.conf import Celery, Mongo, Master, GSServerConf

mongo_conf = {
    'db': 'test',
    'host': 'localhost:27017',
    'username': 'alfrid_db',
    'password': '1234'
}

master_conf = {
    'host': '::',
    'port': 5000

}

mongo = Mongo(**mongo_conf)
master = Master(**master_conf)
celery = Celery(mongo)

conf = GSServerConf(mongo, celery, master)
