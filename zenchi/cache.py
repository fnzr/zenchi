"""Placeholder"""
import sys
import pymongo
from datetime import datetime

this = sys.modules[__name__]
this.db = None
MAX_SERVER_DELAY = 10000


def setup():
    client = pymongo.MongoClient('mongodb://%s:%s@127.0.0.1' %
                                 ('admin', 'admin'),
                                 serverSelectionTimeoutMS=MAX_SERVER_DELAY)
    this.db = client.anidb_cache


def save(command, message, response):
    this.db[command].replace_one(dict(message=message),
                                 dict(message=message,
                                      response=response,
                                      updated=datetime.now()),
                                 upsert=True)


def restore(command, message):
    return this.db[command].find_one(dict(message=message))
