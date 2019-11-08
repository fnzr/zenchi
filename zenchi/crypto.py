""" Thanks https://github.com/adameste/anidbcli """
from Crypto.Cipher import AES
import hashlib
import sys
from . import settings

BS = 16


def pad(s): return s + (BS - len(s) % BS) * chr(BS - len(s) % BS)


def unpad(s): return s[0:-ord(s[-1])]


this = sys.modules[__name__]
this.aes = None


def setup(key):
    md5 = hashlib.md5(bytes(key, "ascii"))
    this.aes = AES.new(md5.digest(), AES.MODE_ECB)


def encrypt(message):
    message = pad(message)
    bytes_message = bytes(message, settings.ENCODING)
    return this.aes.encrypt(bytes_message)


def decrypt(message):
    plain_bytes = this.aes.decrypt(message)
    padded_plain = plain_bytes.decode(settings.ENCODING)
    return unpad(padded_plain)
