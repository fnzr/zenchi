from environs import Env

env = Env()
env.read_env()

ANIDB_SERVER = env.str("ANIDB_SERVER")
ANIDB_PORT = env.int("ANIDB_PORT")

USERNAME = env.str("ANIDB_USERNAME")
PASSWORD = env.str("ANIDB_PASSWORD")
CLIENT_NAME = env.str("ANIDB_CLIENTNAME")
CLIENT_VERSION = env.str("ANIDB_CLIENTVERSION")

USE_CACHE = env.bool("USE_CACHE", True)

ENCRYPT_API_KEY = env.str("ENCRYPT_API_KEY", "")

ENCODING = env.str("ANIDB_ENCODING", "UTF8")

DRY_RUN = env.bool("DRY_RUN", False)
