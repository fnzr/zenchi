"""Placeholder"""
import sys
import pymongo
import logging
from datetime import datetime

this = sys.modules[__name__]
this.db = None
MAX_SERVER_DELAY = 5000

logger = logging.getLogger(__name__)


def setup():
    client = pymongo.MongoClient('mongodb://%s:%s@127.0.0.1' %
                                 ('admin', 'admin'),
                                 serverSelectionTimeoutMS=MAX_SERVER_DELAY)
    try:
        client.admin.command('ismaster')
        this.db = client.anidb_cache
    except pymongo.errors.ConnectionFailure:
        logger.warn(
            "Could not connect to cache server. This is highly unadvised.")
        pass


def save(command, message, response):
    if this.db is None:
        return
    this.db[command].replace_one(dict(message=message),
                                 dict(message=message,
                                      response=response,
                                      updated=datetime.now()),
                                 upsert=True)


def restore(command, message):
    if this.db is None:
        return None
    return this.db[command].find_one(dict(message=message))
