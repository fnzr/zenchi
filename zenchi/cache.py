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
    client = pymongo.MongoClient(serverSelectionTimeoutMS=MAX_SERVER_DELAY)
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


def restore(collection, filter):
    if this.db is None:
        return None
    return this.db[collection].find_one(filter, {'_id': 0})


def update(collection, filter, data):
    this.db[collection].update_one(filter, {'$set': data}, upsert=True)
    return restore(collection, filter)
