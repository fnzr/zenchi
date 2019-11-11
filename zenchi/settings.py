"""Settings dump."""
import sys
import os
from typing import TypeVar

T = TypeVar("T")
this = sys.modules[__name__]

ANIDB_SERVER = os.getenv("ANIDB_SERVER", "")
ANIDB_PORT = int(os.getenv("ANIDB_PORT", 0))

ANIDB_USERNAME = os.getenv("ANIDB_USERNAME", "")
ANIDB_PASSWORD = os.getenv("ANIDB_PASSWORD", "")

ANIDB_ENCRYPT_API_KEY = os.getenv("ANIDB_ENCRYPT_API_KEY", "")

ZENCHI_CLIENTNAME = os.getenv("ZENCHI_CLIENTNAME", "")
ZENCHI_CLIENTVERSION = os.getenv("ZENCHI_CLIENTVERSION", "")

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")


def value_or_error(env_name: str, value: T) -> T:
    """Shorthand method to get the value of a variable from environment.

    Unlike os.getenv, only check value at env_name if value is Falsy.

    :param env_name: name of environment variable to default to if value is not set.
    :type env_name: str
    :param value: the provided value of the variable.
    :type value: T
    :raises ValueError: raised if neither value not Environment Variable is set.
    :return: the value to be used by the variable in the proper context.
    :rtype: T
    """
    if value:
        return value
    env_value: T = getattr(this, env_name, None)
    if env_value:
        return env_value
    raise ValueError(f"{env_name} is required but is not in env nor was a parameter")
