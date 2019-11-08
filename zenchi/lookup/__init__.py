def str_list(data: str):
    return data.split(',')


def int_list(data: str):
    return list(map(lambda x: int(x), str_list(data)))


def to_bool(data: str):
    return True if data == 1 else False
