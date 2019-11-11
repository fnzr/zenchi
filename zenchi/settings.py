"""Settings dump."""
import sys
from typing import TypeVar
from environs import Env

T = TypeVar("T")
this = sys.modules[__name__]

env = Env()
env.read_env()

ANIDB_SERVER = env.str("ANIDB_SERVER")
ANIDB_PORT = env.int("ANIDB_PORT")

ANIDB_USERNAME = env.str("ANIDB_USERNAME")
ANIDB_PASSWORD = env.str("ANIDB_PASSWORD")

ANIDB_ENCRYPT_API_KEY = env.str("ANIDB_ENCRYPT_API_KEY", "")

ZENCHI_CLIENTNAME = env.str("ZENCHI_CLIENTNAME")
ZENCHI_CLIENTVERSION = env.str("ZENCHI_CLIENTVERSION")

MONGODB_URI = env.str("MONGODB_URI", "mongodb://localhost:27017")


def value_or_error(env_name: str, value: T) -> T:
    """Shorthand method to get the value of a variable from environment.

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
