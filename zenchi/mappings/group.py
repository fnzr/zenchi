"""Group mappings."""
from typing import List, Tuple

PARTICIPANT_IN = 1
PARENT_OF = 2
MERGED_FROM = 4
NOW_KNOWN_AS = 5
OTHER = 6


def parse_relations(group_relations: str) -> List[Tuple[int, int]]:
    """Retrieve group relations according to API specification.

    :param group_relations: raw grouprelations string, as sent from API
    :type group_relations: str
    :return: list of (other group id, relation type) tuples
    :rtype: List[Tuple[int, int]]
    """
    relations = group_relations.split("'")
    result = []
    for relation in relations:
        parts = relation.split(",")
        result.append((int(parts[0]), int(parts[1])))
    return result
