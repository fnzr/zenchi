# TODO: parse data types

# Byte 1
AID = 1 << 7 << 48
DATE_FLAGS = 1 << 6 << 48
YEAR = 1 << 5 << 48
TYPE = 1 << 4 << 48
RELATED_AID_LIST = 1 << 3 << 48
RELATED_AID_TYPE = 1 << 2 << 48

# Byte 2
ROMAJI_NAME = 1 << 7 << 40
KANJI_NAME = 1 << 6 << 40
ENGLISH_NAME = 1 << 5 << 40
OTHER_NAME = 1 << 4 << 40
SHORT_NAME = 1 << 3 << 40
SYNONYM_LIST = 1 << 2 << 40

# Byte 3
EPISODES = 1 << 7 << 32
HIGHEST_EPISODE_NUMBER = 1 << 6 << 32
SPECIAL_EP_COUNT = 1 << 5 << 32
AIR_DATE = 1 << 4 << 32
END_DATE = 1 << 3 << 32
URL = 1 << 2 << 32
PICNAME = 1 << 1 << 32

# Byte 4
RATING = 1 << 7 << 24
VOTE_COUNT = 1 << 6 << 24
TEMP_RATING = 1 << 5 << 24
TEMP_VOTE = 1 << 4 << 24
AVERATE_VIEW_RATING = 1 << 3 << 24
REVIEW_COUNT = 1 << 2 << 24
AWARD_LIST = 1 << 1 << 24
IS_18_RESTRICTED = 0 << 24

# Byte 5
ANN_ID = 1 << 6 << 16
ALLCINEMA_ID = 1 << 5 << 16
ANIME_NFO_ID = 1 << 4 << 16
TAG_NAME_LIST = 1 << 3 << 16
TAG_ID_LIST = 1 << 2 << 16
TAG_WEIGHT_LIST = 1 << 1 << 16
DATE_RECORD_UPDATED = 0 << 16

# Byte 6
CHARACTER_ID_LIST = 1 << 7 << 8

# Byte 7
SPECIALS_COUNT = 1 << 7
CREDITS_COUNT = 1 << 6
OTHER_COUNT = 1 << 5
TRAILER_COUNT = 1 << 4
PARODY_COUNT = 1 << 3

lookup = {
    # Byte 1
    AID: 'AID',
    DATE_FLAGS: 'DATE_FLAGS',
    YEAR: 'YEAR',
    TYPE: 'TYPE',
    RELATED_AID_LIST: 'RELATED_AID_LIST',
    RELATED_AID_TYPE: 'RELATED_AID_TYPE',

    # Byte 2
    ROMAJI_NAME: 'ROMAJI_NAME',
    KANJI_NAME: 'KANJI_NAME',
    ENGLISH_NAME: 'ENGLISH_NAME',
    OTHER_NAME: 'OTHER_NAME',
    SHORT_NAME: 'SHORT_NAME',
    SYNONYM_LIST: 'SYNONYM_LIST',

    # Byte 3
    EPISODES: 'EPISODES',
    HIGHEST_EPISODE_NUMBER: 'HIGHEST_EPISODE_NUMBER',
    SPECIAL_EP_COUNT: 'SPECIAL_EP_COUNT',
    AIR_DATE: 'AIR_DATE',
    END_DATE: 'END_DATE',
    URL: 'URL',
    PICNAME: 'PICNAME',

    # Byte 4
    RATING: 'RATING',
    VOTE_COUNT: 'VOTE_COUNT',
    TEMP_RATING: 'TEMP_RATING',
    TEMP_VOTE: 'TEMP_VOTE',
    AVERATE_VIEW_RATING: 'AVERATE_VIEW_RATING',
    REVIEW_COUNT: 'REVIEW_COUNT',
    AWARD_LIST: 'AWARD_LIST',
    IS_18_RESTRICTED: 'IS_18_RESTRICTED',

    # Byte 5
    ANN_ID: 'ANN_ID',
    ALLCINEMA_ID: 'ALLCINEMA_ID',
    ANIME_NFO_ID: 'ANIME_NFO_ID',
    TAG_NAME_LIST: 'TAG_NAME_LIST',
    TAG_ID_LIST: 'TAG_ID_LIST',
    TAG_WEIGHT_LIST: 'TAG_WEIGHT_LIST',
    DATE_RECORD_UPDATED: 'DATE_RECORD_UPDATED',

    # Byte 6
    CHARACTER_ID_LIST: 'CHARACTER_ID_LIST',

    # Byte 7
    SPECIALS_COUNT: 'SPECIALS_COUNT',
    CREDITS_COUNT: 'CREDITS_COUNT',
    OTHER_COUNT: 'OTHER_COUNT',
    TRAILER_COUNT: 'TRAILER_COUNT',
    PARODY_COUNT: 'PARODY_COUNT'
}


def parse_response(input, response):
    result = dict()
    parts = response.split('|')
    part_index = -1
    for i in range(56):
        index = input & (1 << i)
        if index != 0:
            result[lookup[index]] = parts[part_index]
            part_index -= 1
    return result
