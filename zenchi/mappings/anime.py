"""Bytes mapping for masks.

Used in https://wiki.anidb.net/w/UDP_API_Definition#ANIME:_Retrieve_Anime_Data
"""
from typing import Tuple, Dict, Callable, Any, Optional
import logging
from zenchi.mappings import int_list, str_list, to_bool
import zenchi.cache as cache

logger = logging.getLogger(__name__)

# byte 1
aid = 1 << 7 << 48
date_flags = 1 << 6 << 48
year = 1 << 5 << 48
type = 1 << 4 << 48
related_aid_list = 1 << 3 << 48
related_aid_type = 1 << 2 << 48

# byte 2
romaji_name = 1 << 7 << 40
kanji_name = 1 << 6 << 40
english_name = 1 << 5 << 40
other_name = 1 << 4 << 40
short_name = 1 << 3 << 40
synonym_list = 1 << 2 << 40

# byte 3
episodes = 1 << 7 << 32
highest_episode_number = 1 << 6 << 32
special_ep_count = 1 << 5 << 32
air_date = 1 << 4 << 32
end_date = 1 << 3 << 32
url = 1 << 2 << 32
picname = 1 << 1 << 32

# byte 4
rating = 1 << 7 << 24
vote_count = 1 << 6 << 24
temp_rating = 1 << 5 << 24
temp_vote = 1 << 4 << 24
averate_view_rating = 1 << 3 << 24
review_count = 1 << 2 << 24
award_list = 1 << 1 << 24
is_18_restricted = 1 << 24

# byte 5
ann_id = 1 << 6 << 16
allcinema_id = 1 << 5 << 16
anime_nfo_id = 1 << 4 << 16
tag_name_list = 1 << 3 << 16
tag_id_list = 1 << 2 << 16
tag_weight_list = 1 << 1 << 16
date_record_updated = 1 << 16

# byte 6
character_id_list = 1 << 7 << 8

# byte 7
specials_count = 1 << 7
credits_count = 1 << 6
other_count = 1 << 5
trailer_count = 1 << 4
parody_count = 1 << 3

lookup: Dict[int, Tuple[str, Callable[[str], Any]]] = {
    # byte 1
    aid: ("aid", int),
    date_flags: ("date_flags", int),
    year: ("year", str),
    type: ("type", str),
    related_aid_list: ("related_aid_list", str_list),
    related_aid_type: ("related_aid_type", str),
    # byte 2
    romaji_name: ("romaji_name", str),
    kanji_name: ("kanji_name", str),
    english_name: ("english_name", str),
    other_name: ("other_name", str),
    short_name: ("short_name", str_list),
    synonym_list: ("synonym_list", str_list),
    # byte 3
    episodes: ("episodes", int),
    highest_episode_number: ("highest_episode_number", int),
    special_ep_count: ("special_ep_count", int),
    air_date: ("air_date", int),
    end_date: ("end_date", int),
    url: ("url", str),
    picname: ("picname", str),
    # byte 4
    rating: ("rating", int),
    vote_count: ("vote_count", int),
    temp_rating: ("temp_rating", int),
    temp_vote: ("temp_vote", int),
    averate_view_rating: ("averate_view_rating", int),
    review_count: ("review_count", int),
    award_list: ("award_list", str),
    is_18_restricted: ("is_18_restricted", to_bool),
    # byte 5
    ann_id: ("ann_id", int),
    allcinema_id: ("allcinema_id", int),
    anime_nfo_id: ("anime_nfo_id", str),
    tag_name_list: ("tag_name_list", str_list),
    tag_id_list: ("tag_id_list", int_list),
    tag_weight_list: ("tag_weight_list", int_list),
    date_record_updated: ("date_record_updated", int),
    # byte 6
    character_id_list: ("character_id_list", int_list),
    # byte 7
    specials_count: ("specials_count", int),
    credits_count: ("credits_count", int),
    other_count: ("other_count", int),
    trailer_count: ("trailer_count", int),
    parody_count: ("parody_count", int),
}


def parse_response(input: int, response: str) -> Dict[str, Any]:
    """Parse API response to ANIME command into a dictionary.

    :param input: mask used to send the command
    :type input: int
    :param response: string sent as response to the command
    :type response: str
    :return: A variable key dictionary matching what was requested in the mask.
    :rtype: Dict[str, Any]
    """
    result = dict()
    parts = response.split("|")
    part_index = -1
    for i in range(56):
        index = input & (1 << i)
        if index != 0:
            text, function = lookup[index]
            result[text] = function(parts[part_index])
            if part_index + len(parts) == 0:
                break
            part_index -= 1
    return result


def filter_cached(input: int, aid: Optional[int]) -> int:
    """Filter out cached values for ANIME, lessening server load.

    :param input: original requested mask
    :type input: int
    :param aid: anime id
    :type aid: Optional[int]
    :return: new mask with less or igual value.
    :rtype: int
    """
    if aid is None:
        return input
    entry = cache.restore("anime", aid)
    if entry is None:
        return input
    for i in range(56):
        mask = input & (1 << i)
        if mask != 0:
            text, _ = lookup[mask]
            if text in entry:
                input &= ~mask
    return input
