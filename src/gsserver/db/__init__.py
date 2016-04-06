from mongoengine import connect


def init_mongodb(connection):
    # WARN: Do not delete this
    return connect(**connection, connect=False)
