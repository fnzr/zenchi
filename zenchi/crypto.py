""" Thanks https://github.com/adameste/anidbcli """
from typing import Any
from Crypto.Cipher import AES
import hashlib
import sys
from . import settings

BS = 16


def pad(s: str) -> str:
    return s + (BS - len(s) % BS) * chr(BS - len(s) % BS)


def unpad(s: str) -> str:
    return s[0 : -ord(s[-1])]


this = sys.modules[__name__]
aes: Any = None


def setup(key: str) -> None:
    global aes
    md5 = hashlib.md5(bytes(key, "ascii"))
    aes = AES.new(md5.digest(), AES.MODE_ECB)


def encrypt(message: str) -> bytes:
    global aes
    message = pad(message)
    bytes_message = bytes(message, settings.ENCODING)
    return aes.encrypt(bytes_message)  # type: ignore


def decrypt(message: bytes) -> str:
    global aes
    plain_bytes = aes.decrypt(message)
    padded_plain = plain_bytes.decode(settings.ENCODING)
    return unpad(padded_plain)
