"""Bytes mapping for masks.

Used in https://wiki.anidb.net/w/UDP_API_Definition#ANIME:_Retrieve_Anime_Data
"""
from typing import Tuple, Dict, Callable, Any, Optional
import logging
from zenchi.mappings import int_list, str_list, to_bool
import zenchi.cache as cache
from . import mask as amask

logger = logging.getLogger(__name__)

lookup: Dict[int, Tuple[str, Callable[[str], Any]]] = {
    # byte 1
    amask.aid: ("aid", int),
    amask.date_flags: ("date_flags", int),
    amask.year: ("year", str),
    amask.type: ("type", str),
    amask.related_aid_list: ("related_aid_list", str_list),
    amask.related_aid_type: ("related_aid_type", str),
    # byte 2
    amask.romaji_name: ("romaji_name", str),
    amask.kanji_name: ("kanji_name", str),
    amask.english_name: ("english_name", str),
    amask.other_name: ("other_name", str),
    amask.short_name: ("short_name", str_list),
    amask.synonym_list: ("synonym_list", str_list),
    # byte 3
    amask.episodes: ("episodes", int),
    amask.highest_episode_number: ("highest_episode_number", int),
    amask.special_ep_count: ("special_ep_count", int),
    amask.air_date: ("air_date", int),
    amask.end_date: ("end_date", int),
    amask.url: ("url", str),
    amask.picname: ("picname", str),
    # byte 4
    amask.rating: ("rating", int),
    amask.vote_count: ("vote_count", int),
    amask.temp_rating: ("temp_rating", int),
    amask.temp_vote: ("temp_vote", int),
    amask.averate_view_rating: ("averate_view_rating", int),
    amask.review_count: ("review_count", int),
    amask.award_list: ("award_list", str),
    amask.is_18_restricted: ("is_18_restricted", to_bool),
    # byte 5
    amask.ann_id: ("ann_id", int),
    amask.allcinema_id: ("allcinema_id", int),
    amask.anime_nfo_id: ("anime_nfo_id", str),
    amask.tag_name_list: ("tag_name_list", str_list),
    amask.tag_id_list: ("tag_id_list", int_list),
    amask.tag_weight_list: ("tag_weight_list", int_list),
    amask.date_record_updated: ("date_record_updated", int),
    # byte 6
    amask.character_id_list: ("character_id_list", int_list),
    # byte 7
    amask.specials_count: ("specials_count", int),
    amask.credits_count: ("credits_count", int),
    amask.other_count: ("other_count", int),
    amask.trailer_count: ("trailer_count", int),
    amask.parody_count: ("parody_count", int),
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


def filter_cached(input: int, aid: int) -> int:
    """Filter out cached values for ANIME, lessening server load.

    :param input: original requested mask
    :type input: int
    :param aid: anime id
    :type aid: Optional[int]
    :return: new mask with less or igual value.
    :rtype: int
    """
    if not aid:
        return input
    entry = cache.restore("ANIME", aid)
    if entry is None:
        return input
    for i in range(56):
        mask = input & (1 << i)
        if mask != 0:
            text, _ = lookup[mask]
            if text in entry:
                input &= ~mask
    return input
