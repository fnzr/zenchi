"""Extremely basic "cache".

Really, I just dump it on the database.
"""
from typing import Any, Dict, Optional, Union
import sys
import pymongo
import logging
from datetime import datetime

db: Any = None
MAX_SERVER_DELAY = 5000

logger = logging.getLogger(__name__)


def setup() -> None:
    """Create connection to mongo database.

    Will send an warning if the connection is not successfull, but will proceed just fine.
    You really should use some kind of cache though.
    
    :return: [description]
    :rtype: None
    """
    global db
    client = pymongo.MongoClient(serverSelectionTimeoutMS=MAX_SERVER_DELAY)
    try:
        client.admin.command("ismaster")
        db = client.anidb_cache
    except pymongo.errors.ConnectionFailure:
        logger.warn("Could not connect to cache server. This is highly unadvised.")
        pass


def restore(collection: str, id: Union[str, int]) -> Optional[Dict[str, Any]]:
    """Restrieve cached data from database.
    
    :param collection: The collection to be retrieved. Same name as API commands.
    :type collection: str
    :param id: The unique identifier for a particular collection. This varies by command.
    :type id: Union[str, int]
    :return: The retrieved data if exists, else None.
    :rtype: Optional[Dict[str, Any]]
    """
    global db
    if db is None:
        return None
    return db[collection].find_one(dict(_id=id), dict(_id=0))  # type: ignore


def update(
    collection: str, id: Union[str, int], data: Dict[str, Any]
) -> Dict[str, Any]:
    """Create and/or update data in database.

    :param collection: The collection to be retrieved. Same name as API commands.
    :type collection: str
    :param id: The unique identifier for a particular collection. This varies by command.
    :type id: Union[str, int]
    :param data: The data to be added into the database. There's no safety checking here, pump and dump.
    :type data: Dict[str, Any]
    :return: The created/updated entry.
    :rtype: Dict[str, Any]
    """

    global db
    db[collection].update_one(dict(_id=id), {"$set": data}, upsert=True)
    return restore(collection, id)  # type: ignore
