import logging
import anidb


def main():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    api = anidb.API(14443, '')
    #api.ping()
    #api.ping()
    #api.anime(1)


if __name__ == '__main__':
    main()
