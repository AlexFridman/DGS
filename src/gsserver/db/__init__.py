from mongoengine import connect


def init_mongodb(connection):
    return connect(**connection)
