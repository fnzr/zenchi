from environs import Env

env = Env()
env.read_env()

USERNAME = env.str("ANIDB_USERNAME")
PASSWORD = env.str("ANIDB_PASSWORD")
CLIENT_NAME = env.str("ANIDB_CLIENTNAME")
CLIENT_VERSION = env.str("ANIDB_CLIENTVERSION")

USE_CACHE = env.bool("USE_CACHE", True)
