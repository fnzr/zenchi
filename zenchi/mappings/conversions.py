"""Generic conversions used everywhere."""
from typing import List


def str_list(data: str) -> List[str]:
    """Generate a string list.

    :param data: comma separated string of strings.
    :type data: str
    :return: List[str]
    :rtype: List[str]
    """
    return data.split(",")


def int_list(data: str) -> List[int]:
    """Generate a int list.

    :param data: comma separated string of ints
    :type data: str
    :return: List. of int.
    :rtype: List[int]
    """
    listed = str_list(data)
    if listed[0]:
        return list(map(lambda x: int(x), listed))
    return []


def to_bool(data: str) -> bool:
    """Convert only '1' to True, else False.

    :param data: Usually part of API response.
    :type data: str
    :return: Take a guess.
    :rtype: bool
    """
    return True if data == "1" else False
