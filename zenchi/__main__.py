import logging
import anidb
import lookup.anime as alookup
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s][%(levelname)s] %(name)s: %(message)s")

s_handler = logging.StreamHandler()
f_handler = logging.FileHandler("log.txt")
f_handler.setLevel(logging.INFO)
s_handler.setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)
logger.addHandler(s_handler)
logger.addHandler(f_handler)


def main():
    api = anidb.API(14443, 'hpGJG', False)
    #api.ping(skip_cache=False)
    #api.ping()
    amask = alookup.AID | alookup.YEAR | alookup.ROMAJI_NAME | alookup.ENGLISH_NAME
    api.anime(amask, aid=1)


if __name__ == '__main__':
    main()
