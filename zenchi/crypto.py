"""Mostly copied from smarter people than I.

Thanks https://github.com/adameste/anidbcli
"""
from typing import Any
from Crypto.Cipher import AES
import hashlib

BS = 16


def pad(s: str) -> str:
    """Pad string with PKCS5Padding scheme.

    :param s: string to be padded
    :type s: str
    :return: padded string
    :rtype: str
    """
    return s + (BS - len(s) % BS) * chr(BS - len(s) % BS)


def unpad(s: str) -> str:
    """Unpad string.

    :param s: string to be unpadded
    :type s: str
    :return: unpadded string
    :rtype: str
    """
    return s[0: -ord(s[-1])]


aes: Any = None


def setup(key: str) -> None:
    """Generate aes object with given key.

    :param key: api_key of user plus provided salt from ENCRYPT command
    :type key: str
    :rtype: None
    """
    global aes
    md5 = hashlib.md5(bytes(key, "ascii"))
    aes = AES.new(md5.digest(), AES.MODE_ECB)


def encrypt(message: str, encoding: str) -> bytes:
    """Encrypt message to be sent to server. setup MUST be called first.

    :param message: message to be encrypted.
    :type message: str
    :param encoding:
    :type message: str
    :return: encrypted message to be sent
    :rtype: bytes
    """
    global aes
    message = pad(message)
    bytes_message = bytes(message, encoding)
    return aes.encrypt(bytes_message)  # type: ignore


def decrypt(message: bytes, encoding: str) -> str:
    """Decrypt message received from server. setup MUST be called first.

    :param message: message to be decrypted.
    :type message: bytes
    :param encoding:
    :type message: str
    :return: decrypted message
    :rtype: str
    """
    global aes
    plain_bytes = aes.decrypt(message)
    padded_plain = plain_bytes.decode(encoding)
    return unpad(padded_plain)
