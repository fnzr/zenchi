from typing import List


def str_list(data: str) -> List[str]:
    return data.split(",")


def int_list(data: str) -> List[int]:
    listed = str_list(data)
    if listed[0]:
        return list(map(lambda x: int(x), listed))
    return []


def to_bool(data: str) -> bool:
    return True if data == 1 else False
