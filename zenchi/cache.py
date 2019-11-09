"""Placeholder"""
from typing import Any, Dict, Optional, Union
import sys
import pymongo
import logging
from datetime import datetime

db: Any = None
MAX_SERVER_DELAY = 5000

logger = logging.getLogger(__name__)


def setup() -> None:
    global db
    client = pymongo.MongoClient(serverSelectionTimeoutMS=MAX_SERVER_DELAY)
    try:
        client.admin.command("ismaster")
        db = client.anidb_cache
    except pymongo.errors.ConnectionFailure:
        logger.warn("Could not connect to cache server. This is highly unadvised.")
        pass


def restore(collection: str, id: Union[str, int]) -> Optional[Dict[str, Any]]:
    global db
    if db is None:
        return None
    return db[collection].find_one(dict(_id=id), dict(_id=0))  # type: ignore


def update(
    collection: str, id: Union[str, int], data: Dict[str, Any]
) -> Dict[str, Any]:
    global db
    db[collection].update_one(dict(_id=id), {"$set": data}, upsert=True)
    return restore(collection, id)  # type: ignore
