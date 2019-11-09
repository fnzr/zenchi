from typing import List


def str_list(data: str) -> List[str]:
    return data.split(",")


def int_list(data: str) -> List[int]:
    return list(map(lambda x: int(x), str_list(data)))


def to_bool(data: str) -> bool:
    return True if data == 1 else False
