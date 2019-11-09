"""Placeholder
"""
from typing import Callable, Any, Dict, Tuple, Union, Optional, cast, Iterator
import socket
import logging
import threading
from functools import wraps
from time import sleep
from zenchi import cache, settings
from zenchi.lookup import anime as alookup
from zenchi.lookup import int_list
import zenchi.crypto as crypto
import zenchi.errors as errors

logger = logging.getLogger(__name__)

MAX_RECEIVE_SIZE = 4096
PROTOVER_PARAMETER = 3


EndpointDict = Dict[str, Any]
EndpointResult = Tuple[EndpointDict, int]
PacketParameters = Dict[str, Union[str, int]]

_conn: Optional[socket.socket] = None
_encrypted_session = False
_session = ""


def _listen_incoming_packets() -> Iterator[bytes]:
    s = get_socket()
    while True:
        yield s.recv(MAX_RECEIVE_SIZE)
    return b""


def create_socket(host: str = "", port: int = 14443) -> socket.socket:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((host, port))
    anidb_host = settings.ANIDB_SERVER
    anidb_port = settings.ANIDB_PORT
    s.connect((anidb_host, anidb_port))
    logger.info(
        f"Created socket on UDP %s:%d => %s:%d", host, port, anidb_host, anidb_port
    )
    return s


def get_socket() -> socket.socket:
    global _conn
    if _conn is None:
        _conn = create_socket()
    return _conn


def send(
    command: str,
    args: PacketParameters,
    callback: Callable[[int, str], Optional[EndpointDict]],
    requires_auth: bool = False,
) -> EndpointResult:
    """Sends an UDP packet to endpoint and synchronously wait and reads a response.

    See https://wiki.anidb.net/w/UDP_API_Definition

    Args:
        command (str): API command. Ex: PING
        args (dict): Dicionary of arguments to be sent in the packet.
            Will be sent as string according to ENCODING.
            Ex: dict(foo=1, bar=2) => foo=1&bar=2
        callback (Callable[[int, str], dict]): Each command has
            its own rules for parsing the API response, so it receives
            the code and the raw response and returns the parsed response.
            This callback in defined in each endpoint.
            Do note that most errors are handled in the decorator endpoint.
        requires_auth (bool): Endpoint requires auth and session will be 
            checked and appended to args if needed.
    Returns:
        dict: Whatever callback returns.
    """
    if requires_auth:
        if _session:
            args["s"] = _session
        else:
            raise errors.EndpointError(
                ("This endpoint requires a session. " "Call .auth() to acquire one.")
            )
    socket = get_socket()
    message = "&".join([f"{key}={value}" for key, value in args.items()])
    data = f"{command} {message}"
    logger.info("Sending %s", data)

    global _encrypted_session
    if _encrypted_session:
        packet = crypto.encrypt(data)
    else:
        packet = data.encode(settings.ENCODING)
    socket.send(packet)
    raw_response = next(_listen_incoming_packets())

    if _encrypted_session:
        api_response = crypto.decrypt(raw_response)
    else:
        api_response = raw_response.decode(settings.ENCODING)
    logger.debug(api_response)

    code = int(api_response[:3])
    result = callback(code, api_response)
    if result is not None:
        logger.debug(data)
        return result, code
    if code == 505:
        raise errors.IllegalParameterError
    if code == 598:
        raise errors.IllegalCommandError
    if code == 555:
        raise errors.BannedError(api_response.splitlines()[1])
    if code == 502:
        raise errors.InvalidCredentialsError
    if code in (501, 506):
        logger.info("[%d] Invalid or expired session. Trying to login.", code)
        auth()
        return send(command, args, callback)
    if code in (600, 601, 602):
        logger.info("[%d] Server unavailable. Delaying and resending.", code)
        sleep(30)
        return send(command, args, callback)
    if code == 604:
        logger.info("[%d] Server timeout. Delaying and resending.", code)
        sleep(5)
        return send(command, args, callback)
    raise errors.UnhandledResponseError(api_response)


def auth(
    username: Optional[str] = None,
    password: Optional[str] = None,
    client_name: Optional[str] = None,
    client_version: Optional[str] = None,
    nat: Optional[int] = None,
    attempt: int = 1,
) -> EndpointResult:
    """Obtains new session.
        See https://wiki.anidb.net/w/UDP_API_Definition#AUTH:_Authing_to_the_AnimeDB # noqa

    Args:
        username (str, optional): Defaults to $ANIDB_USERNAME.
        password (str, optional): Defaults to $ANIDB_PASSWORD.
        client_name (str, optional): Defaults to $ANIDB_CLIENTNAME.
        client_version (str, optional): Defaults to $ANIDB_CLIENTVERSION.
        nat (int, optional): Defaults to 0.
        attempt (int, optional): Used to retry authentication and prevent
            server flood.

    Raises:
        ValueError: Fired if max number of attempts to login was reached
            Server keeps asking to retry, but fails to deliver a session.
        errors.APIError: Fired if client is outdated.
            Either the client is outdated or this script is.

    Returns:
        {
            code: int,
            session: str,
            nat: str or None
        }
    """
    if attempt > 5:
        raise errors.EndpointError("Could not login after 5 attempts. Giving up.")
    data = {
        "user": settings.USERNAME if username is None else username,
        "pass": settings.PASSWORD if password is None else password,
        "protover": PROTOVER_PARAMETER,
        "client": settings.CLIENT_NAME if client_name is None else client_name,
        "clientver": settings.CLIENT_VERSION
        if client_version is None
        else client_version,
        "enc": settings.ENCODING,
    }
    if nat is not None:
        data["nat"] = nat

    def cb(code: int, response: str) -> Optional[EndpointDict]:
        if code == 503:
            raise errors.ClientOutdatedError
        if code == 504:
            reason = response.split("-")[1].strip()
            raise errors.ClientBannedError(reason)
        if code in (200, 201):
            parts = response.split(" ")
            global _session
            _session = parts[1]
            nat_info = parts[2] if nat == 1 else None
            return dict(session=_session, nat=nat_info)
        return None

    return send("AUTH", data, cb)


def logout() -> EndpointResult:
    """Logout. See https://wiki.anidb.net/w/UDP_API_Definition#LOGOUT:_Logout

    Returns:
        {
            code: int
        }
    """

    def cb(code: int, response: str) -> Optional[EndpointDict]:
        if code in (403, 203):
            global _session
            _session = ""
            return dict(message=response[3:].strip())
        return None

    return send("LOGOUT", {}, cb, True)


def encrypt(
    username: Optional[str] = None, api_key: Optional[str] = None, type: int = 1,
) -> EndpointResult:
    api_key = settings.ENCRYPT_API_KEY if api_key is None else api_key
    username = settings.USERNAME if username is None else username
    if api_key is None or not api_key:
        raise errors.EndpointError(
            (
                "Requested ENCRYPT but no api_key provided. "
                "Set $ENCRYPT_API_KEY or pass as argument"
            )
        )

    def cb(code: int, response: str) -> Optional[EndpointDict]:
        if code in (309, 509, 394):
            return dict(message=response[3:].strip())
        if code == 209:
            salt = response.split(" ")[1].strip()
            crypto.setup(api_key + salt)  # type: ignore
            global _encrypted_session
            _encrypted_session = True
            logger.info("Successfully registered encryption.")
            return dict(salt=salt)
        return None

    return send("ENCRYPT", dict(user=username, type=type), cb)


def encoding(name: str) -> EndpointResult:
    """Sets the encoding for the session. Used if session was restored.
    See https://wiki.anidb.net/w/UDP_API_Definition#ENCODING:_Change_Encoding_for_Session # noqa

    Args:
        name (str): Encoding name

    Raises:
        errors.APIError: Raised if encoding is not valid

    Returns:
        {
            code: int
        }
    """

    def cb(code: int, response: str) -> Optional[EndpointDict]:
        if code in (519, 219):
            return dict(message=response[3:].strip())
        return None

    return send("ENCODING", dict(name=name), cb)


def ping(nat: Optional[int] = None) -> EndpointResult:
    """Pings the server.
    See https://wiki.anidb.net/w/UDP_API_Definition#PING:_Ping_Command

    Args:
        nat (int, optional): Any value here means true.

    Returns:
        {
            code: int,
            port: int | None
        }: Server response.
    """

    def cb(code: int, response: str) -> Optional[EndpointDict]:
        if code == 300:
            port = int(response.split("\n")[1]) if nat else None
            return dict(port=port)
        return None

    data: PacketParameters = {} if nat is None else dict(nat=nat)
    return send("PING", data, cb)


def anime(
    amask: int, aid: Optional[int] = None, aname: Optional[str] = None
) -> EndpointResult:
    """Retrieve anime data according to aid or aname.

    See https://wiki.anidb.net/w/UDP_API_Definition#ANIME:_Retrieve_Anime_Data # noqa

    Args:
        aid (int, optional)
        aname (str, optional)
        amask (int, optional): 56bit integer

    Raises:
        ValueError: Raised if neither aid and aname are provided.

    Returns:
        {
            code: int
            ...
        }: Dynamic dictionary, built according to amask parameter.
        See lookup.anime for all options.
    """
    if aid is None and aname is None:
        raise errors.EndpointError("Either aid or aname must be provided")
    command = "ANIME"

    def cb(code: int, response: str) -> Optional[EndpointDict]:
        if code == 330:
            return dict(message=response[3:].strip())
        if code == 230:
            content = response.splitlines()[1]
            result = alookup.parse_response(amask, content)
            if aid:
                return cache.update(command, aid, result)
            else:
                return result
        return None

    filtered_mask = alookup.filter_cached(amask, aid)
    data: PacketParameters = dict(amask=format(filtered_mask, "x"))
    if aid is not None:
        if filtered_mask == 0:
            restored = cache.restore(command, aid)
            if restored is not None:
                return restored, 230
        data["aid"] = aid
    elif aname is not None:
        data["aname"] = aname
        logger.warning(
            (
                "Using aname to search for ANIME prevents cache from working"
                "Consider using aid instead."
            )
        )
    return send(command, data, cb, True)


def animedesc(aid: int, part: int) -> EndpointResult:
    command = "ANIMEDESC"
    id = f"{aid}|{part}"

    def cb(code: int, response: str) -> Optional[EndpointDict]:
        if code in (330, 330):
            return dict(message=response[3:].strip())
        if code == 233:
            parts = response.splitlines()[1].split("|")
            result = {
                "current_part": int(parts[0]),
                "max_parts": int(parts[1]),
                "description": parts[2],
            }
            cache.update(command, id, result)
            return result
        return None

    entry = cache.restore(command, id)
    if entry is None:
        data: PacketParameters = dict(aid=aid, part=part)
        return send(command, data, cb, True)
    return entry, 233


def character(charid: int) -> EndpointResult:
    command = "CHARACTER"

    def cb(code: int, response: str) -> Optional[EndpointDict]:
        if code == 335:
            return dict(message=response[3:].strip())
        if code == 235:
            data = response.splitlines()[1].split("|")
            result = {
                "charid": int(data[0]),
                "name_kanji": data[1],
                "name_transcription": data[2],
                "pic": data[3],
                "episode_list": int_list(data[5]),
                "last_updated_date": int(data[6]),
                "type": int(data[7]),
                "gender": data[8],
            }
            blocks = []
            raw_blocks = data[4].split("'")
            for block in raw_blocks:
                parts = block.split(",")
                blocks.append(
                    {
                        "anime_id": int(parts[0]),
                        "appearance": int(parts[1]),
                        "creator_id": int(parts[2]),
                        "is_main_seyuu": bool(parts[3]) if parts[3] else None,
                    }
                )
            result["anime_blocks"] = blocks
            return cache.update(command, charid, result)
        return None

    entry = cache.restore(command, charid)
    if entry is None:
        return send(command, dict(charid=charid), cb, True)
    return entry, 235

