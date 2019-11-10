"""Placeholder."""
from typing import (
    Callable,
    Any,
    Dict,
    Tuple,
    Union,
    Optional,
    Iterator,
    TypeVar,
)
import socket
import logging
from time import sleep
from zenchi import cache, settings
import zenchi.mappings as mappings
from zenchi.mappings import int_list
import zenchi.crypto as crypto
import zenchi.errors as errors
from zenchi.codes import response_message

logger = logging.getLogger(__name__)

MAX_RECEIVE_SIZE = 4096
PROTOVER_PARAMETER = 3


T = TypeVar("T")
EndpointDict = Dict[str, Any]
EndpointResult = Tuple[EndpointDict, int]
PacketParameters = Dict[str, Union[str, int]]

_conn: Optional[socket.socket] = None
_encryptedsession = False
_encoding = "UTF8"
_session = ""

PUBLIC_COMMANDS = ["PING", "ENCRYPT", "ENCODING", "AUTH", "VERSION"]


def value_or_error(env_name: str, value: T) -> T:
    """Shorthand method to check is a variable has appropriate value.

    :param env_name: name of environment variable to default to if value is not set.
    :type env_name: str
    :param value: the provided value of the variable.
    :type value: T
    :raises ValueError: raised if neither value not Environment Variable is set.
    :return: the value to be used by the variable in the proper context.
    :rtype: T
    """
    if value:
        return value
    env_value: T = settings.__dict__[env_name]
    if env_value:
        return env_value
    raise ValueError(f"{env_name} is required but is not in env nor was a parameter")


def _listen_incoming_packets() -> Iterator[bytes]:
    """Wait until received a packet from the server.

    TODO: this hangs indefinetely if no data is received.

    :return: The raw data from the server.
    :rtype: Iterator[bytes]
    """
    s = get_socket()
    s.settimeout(30)
    while True:
        yield s.recv(MAX_RECEIVE_SIZE)
    return b""


def create_socket(
    host: str = "", port: int = 14443, anidb_server: str = "", anidb_port: int = 0
) -> socket.socket:
    """Create a socket to be use to communicate with the server.

    This function is called internally, so you only have to call it if you want to change the default parameters.

    :param host: local host to bind the socket to, defaults to "" (which I think is any. Read the docs.)
    :type host: str, optional
    :param port: local port to bind the socket to, defaults to 14443
    :type port: int, optional
    :param anidb_server: aniDB server name, defaults to environment ANIDB_SERVER
    :type anidb_server: str, optional
    :param anidb_port: anidb port, default to environment ANIDB_PORT
    :type anidb_port: int, optional
    :return: The created socket.
    :rtype: socket.socket
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((host, port))
    anidb_server = value_or_error("ANIDB_SERVER", anidb_server)
    anidb_port = value_or_error("ANIDB_PORT", anidb_port)
    s.connect((anidb_server, anidb_port))
    logger.info(
        f"Created socket on UDP %s:%d => %s:%d", host, port, anidb_server, anidb_port
    )
    global _conn
    _conn = s
    return s


def get_socket() -> socket.socket:
    """Create socket if doesn't exist. Returns it.

    :return: Socket used for all communication with the server.
    :rtype: socket.socket
    """
    global _conn
    if _conn is None:
        _conn = create_socket()
    return _conn


def send(
    command: str,
    args: PacketParameters,
    callback: Callable[[int, str], Optional[EndpointDict]],
) -> EndpointResult:
    """Send an UDP packet to endpoint and synchronously wait and reads a response.

    See https://wiki.anidb.net/w/UDP_API_Definition

    :param command: the first word to be sent to the server
    :type command: str
    :param args: a dictionary o parameters that will be sent to the server, name=value
    :type args: PacketParameters
    :param callback: the response handler.
    :type callback: Callable[[int, str], Optional[EndpointDict]]
    :raises ValueError: [description]
    :raises errors.APIError: this actually raises specific Errors according to response code.
        If this was raised, the server rejected the request for some reason.
    :raises ValueError: raised if there was an attempt to send a request to a restricted endpoint without authenticating first.
    Call auth() and repeat the request.
    :return: a tuple (data, code). See docs of specific commands for details.
    :rtype: EndpointResult
    """
    if command not in PUBLIC_COMMANDS:
        if _session:
            args["s"] = _session
        else:
            raise ValueError(
                "Trying to send a command that requires a session without calling auth() first"
            )
    socket = get_socket()
    message = "&".join([f"{key}={value}" for key, value in args.items()])
    data = f"{command} {message}"
    logger.info("Sending %s", data)

    global _encryptedsession
    if _encryptedsession:
        packet = crypto.encrypt(data, _encoding)
    else:
        packet = data.encode(_encoding)
    socket.send(packet)
    raw_response = next(_listen_incoming_packets())

    if _encryptedsession:
        api_response = crypto.decrypt(raw_response, _encoding)
    else:
        api_response = raw_response.decode(_encoding)
    logger.debug(api_response)

    code = int(api_response[:3])
    result = callback(code, api_response)
    if result is not None:
        return result, code
    if code == 505:
        raise errors.IllegalParameterError
    if code == 598:
        raise errors.IllegalCommandError
    if code == 555:
        raise errors.BannedError(api_response.splitlines()[1])
    if code == 502:
        raise errors.InvalidCredentialsError
    if code in (600, 601, 602):
        raise errors.ServerUnavailableError(code)
    if code == 501:
        logger.info("501 LOGIN FIRST. Sending auth and retrying.")
        auth()
        return send(command, args, callback)
    if code == 506:
        if "s" in args:
            logger.info("506 INVALID SESSION. Sending auth and retying")
            auth()
            return send(command, args, callback)
        else:
            raise errors.InvalidSessionError
    if code == 604:
        logger.info("[%d] Server timeout. Delaying and resending.", code)
        sleep(5)
        return send(command, args, callback)
    raise errors.UnhandledResponseError(api_response)


def restore_session(session: str, enc: str = 'UTF8') -> EndpointResult:
    """Set current session to `session` and call ENCODING command.

    WARNING: it technically works but if a new socket was created and/or the outgoing
    port changed (external, not internal), the server sends 501 in the first non-public endpoint.
    I think.

    :param session: the string obtained from a previous session.
    :type session: str
    :param enc: encoding to be used in the session.
    :return: the result of a ENCODING command.
    :rtype: EndpointResult
    """
    global _encoding
    _encoding = enc

    global _session
    _session = session
    return encoding(_encoding)


def auth(
    username: str = "",
    password: str = "",
    client_name: str = "",
    client_version: str = "",
    nat: bool = False,
    encoding: str = "UTF8",
) -> EndpointResult:
    """Create a new session for authentication.

    See https://wiki.anidb.net/w/UDP_API_Definition#AUTH:_Authing_to_the_AnimeDB

    :param username: anidb user. Defaults to environment ANIDB_USERNAME
    :type username: str, optional
    :param password: anidb password. Defaults to environment ANIDB_USERNAME
    :type password: str, optional
    :param client_name: zenchi client name. Defaults to environment ZENCHI_CLIENTNAME
    :type client_name: str, optional
    :param client_version: zenchi client version. Defaults to environment ZENCHI_CLIENTVERSION
    :type client_version: str, optional
    :param nat: should request nat info, defaults to False
    :type nat: bool, optional
    :param encoding: encoding to be used during the session. Default to UTF8
    :type encoding: str, optional
    :raises errors.ClientOutdatedError:
    :raises errors.ClientBannedError:
    :raises ValueError: raised if any of the parameters is not set
    :return: A tuple (data, code). data is a dictionary with the keys:
        :session str: The session provided by the server. Will be used in all future commands
            that require authentication.
        :nat Optional[str]: Present only if nat=1. String `ip:port`.
    :rtype: EndpointResult
    """
    global _enconding
    _encoding = encoding
    data: Dict[str, Union[str, int]] = {
        "user": value_or_error("ANIDB_USERNAME", username),
        "pass": value_or_error("ANIDB_PASSWORD", password),
        "client": value_or_error("ZENCHI_CLIENTNAME", client_name),
        "clientver": value_or_error("ZENCHI_CLIENTVERSION", client_version),
        "protover": PROTOVER_PARAMETER,
        "enc": _encoding,
    }

    if nat:
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
            result = dict(session=_session)
            if nat:
                result["nat"] = parts[2]
            return result
        return None

    return send("AUTH", data, cb)


def logout() -> EndpointResult:
    """Clear the session and invalidates it to the server.

    See https://wiki.anidb.net/w/UDP_API_Definition#LOGOUT:_Logout

    :return: A tuple (data, code). data is a dictionary with the keys:
        :message str: the returned message from the server.
    :rtype: EndpointResult
    """

    def cb(code: int, response: str) -> Optional[EndpointDict]:
        if code in (403, 203):
            global _session
            _session = ""
            return dict(message=response_message[code])
        return None

    return send("LOGOUT", {}, cb)


def encrypt(username: str = "", api_key: str = "", type: int = 1) -> EndpointResult:
    """Enable encrypted communication with the server until new connection or logout.

    See https://wiki.anidb.net/w/UDP_API_Definition#ENCRYPT:_Start_Encryptedsession

    :param username: anidb user. Defaults to environment ANIDB_USERNAME
    :type username: str, optional
    :param api_key: anidb user. Defaults to environment ANIDB_ENCRYPT_API_KEY
    :type api_key: str, optional
    :param type: required for command. Do not modify. Defaults to 1
    :type type: int, optional
    :return: A tuple (data, code).
        If the command is successful, data is a dictionary with the keys:
            :salt str: salt to be used with api_key to encrypt and decrypt future messages.
        If not:
            :message str: the reason why the command failed.
    :rtype: EndpointResult
    """
    api_key = value_or_error("ENCRYPT_API_KEY", api_key)
    username = value_or_error("ANIDB_USERNAME", username)

    def cb(code: int, response: str) -> Optional[EndpointDict]:
        if code in (309, 509, 394):
            return dict(message=response_message[code])
        if code == 209:
            salt = response.split(" ")[1].strip()
            crypto.setup(api_key + salt)
            global _encryptedsession
            _encryptedsession = True
            logger.info("Successfully registered encryption.")
            return dict(salt=salt)
        return None

    return send("ENCRYPT", dict(user=username, type=type), cb)


def encoding(name: str) -> EndpointResult:
    """Set the encoding for the session. Should be used only when restoring existing session.

    See https://wiki.anidb.net/w/UDP_API_Definition#ENCODING:_Change_Encoding_forsession # noqa

    TODO: is it even possible to "restore" a session?

    :param name: encoding name
    :type name: str
    :return: A tuple (data, code). data is a dictionary with the keys:
        :message str: the server response.
    :rtype: EndpointResult
    """

    def cb(code: int, response: str) -> Optional[EndpointDict]:
        if code in (519, 219):
            return dict(message=response_message[code])
        return None

    return send("ENCODING", dict(name=name), cb)


def ping(nat: bool = False) -> EndpointResult:
    """Ping the server.

    See https://wiki.anidb.net/w/UDP_API_Definition#PING:_Ping_Command

    :param nat: determine if server should inform the outgoing port. Defaults to False.
    :type nat: bool
    :return: A tuple (data, code). data is a dictionary with the key:
        if nat:
            :port int: the outgoing port as seen by the server.
        otherwise, empty.
    :rtype: EndpointResult
    """

    def cb(code: int, response: str) -> Optional[EndpointDict]:
        if code == 300:
            if nat:
                return dict(port=int(response.split("\n")[1]))
            else:
                return {}
        return None

    data: PacketParameters = dict(nat=1) if nat else {}
    return send("PING", data, cb)


def anime(
    amask: int, aid: int = 0, aname: str = '', use_cache: bool = True
) -> EndpointResult:
    """Retrieve anime data according to mask.

    See https://wiki.anidb.net/w/UDP_API_Definition#ANIME:_Retrieve_Anime_Data

    :param amask: an encoded int the defines what will be requested from the server.
        Preferably created by using mappings.anime module. For example:
            amask = aid | episodes | year | english_name | rating
        Before sending the parameter to the server, this value is filtered against the local cache,
        preventing the request of repeated data.
        This means the provided mask and the sent mask will not necessarily match.
    :type amask: int
    :param aid: anidb id of anime. Defaults to None
    :type aid: Optional[int]
    :param aname: search by anime name, must match perfectly. Avoid using this. Defaults to None.
    :type aname: Optional[str]
    :raises ValueError: raised if neither aid and aname are provided.
    :return: A tuple (data, code). data is a dictionary with the keys:
        if no anime was found:
            :message str: "NO SUCH ANIME"
        if anime was found, a dictionary with the keys matching the requested data.
        TODO: currently, if some anime data is in the cache, ALL anime data is returned.
    :rtype: EndpointResult
    """
    command = "ANIME"
    if use_cache:
        filtered_mask = mappings.anime.filter_cached(amask, aid)
    else:
        filtered_mask = amask
    data: PacketParameters = dict(amask=format(filtered_mask, "x"))
    if aid:
        if filtered_mask == 0:
            restored = cache.restore(command, aid)
            if restored is not None:
                return restored, 230
        data["aid"] = aid
    elif aname:
        data["aname"] = aname
        logger.warning(
            (
                "Using aname to search for ANIME prevents cache from working"
                "Consider using aid instead."
            )
        )
    else:
        raise ValueError("Either aid or aname must be provided")

    def cb(code: int, response: str) -> Optional[EndpointDict]:
        if code == 330:
            return dict(message=response_message[code])
        if code == 230:
            content = response.splitlines()[1]
            result = mappings.anime.parse_response(amask, content)
            if aid:
                return cache.update(command, aid, result)
            else:
                return result
        return None

    return send(command, data, cb)


def animedesc(aid: int, part: int, use_cache: bool = True) -> EndpointResult:
    """Retrieve partial anime description.

    See https://wiki.anidb.net/w/UDP_API_Definition#ANIMEDESC:_Retrieve_Anime_Description

    :param aid: anidb id of anime.
    :type aid: int
    :param part: part of the description. One description might span several parts.
    :type part: int
    :return: A tuple (data, code). data is a dictionary with the keys:
        if successful:
            :current_part int: the requested part
            :max_parts int: the number of parts of this description.
            :description str: the description.
        if not:
            :message str: reason.
    :rtype: EndpointResult
    """
    command = "ANIMEDESC"
    id = f"{aid}|{part}"

    def cb(code: int, response: str) -> Optional[EndpointDict]:
        if code in (330, 330):
            return dict(message=response_message[code])
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
    if not use_cache or entry is None:
        data: PacketParameters = dict(aid=aid, part=part)
        return send(command, data, cb)
    return entry, 233


def character(charid: int, use_cache: bool = True) -> EndpointResult:
    """Retrieve character details.

    See https://wiki.anidb.net/w/UDP_API_Definition#CHARACTER:_Get_Character_Information

    :param charid: anidb id of the character.
    :type charid: int
    :return: A tuple (data, code). data is a dictionary with the keys:
        if code == 335:
            :message str: NO SUCH CHARACTER
        if code == 235:
            For details, see link above.
            :charid int:
            :name_kanki str:
            :name_transcription str:
            :pic:
            :episode_list List[int]:
            :last_updated_date int:
            :type int:
            :gender str:
            :anime_blocks List[Dictionary]:
        Each anime block has the following keys:
            :anime_id int:
            :appearance int:
            :creator_id int:
            :is_main_seyuu bool or None:
    :rtype: EndpointResult
    """
    command = "CHARACTER"

    def cb(code: int, response: str) -> Optional[EndpointDict]:
        if code == 335:
            return dict(message=response_message[code])
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
    if not use_cache or entry is None:
        return send(command, dict(charid=charid), cb)
    return entry, 235


def calendar() -> EndpointResult:
    """Retrieve recently aired and upcoming shows.

    See https://wiki.anidb.net/w/UDP_API_Definition#CALENDAR:_Get_Upcoming_Titles

    :return: a tuple (data, code). data is a dictionary with the keys:
        if code == 397:
            :message str: CALENDAR EMPTY
        if code == 297:
            :calendar List[Dictionary]:
        Each calendar entry has the following keys:
            :aid int:
            :startdate int:
            :dateflags int:
    :rtype: EndpointResult
    """

    def cb(code: int, response: str) -> Optional[EndpointDict]:
        if code == 397:
            return dict(message=response_message[code])
        if code == 297:
            lines = response.splitlines()[1:]
            result = []
            for line in lines:
                parts = line.split("|")
                result.append(
                    {
                        "aid": int(parts[0]),
                        "startdate": int(parts[1]),
                        "dateflags": int(parts[2]),
                    }
                )
            return dict(calendar=result)
        return None

    return send("CALENDAR", {}, cb)


def creator(creatorid: int, use_cache: bool = True) -> EndpointResult:
    """Retrieve creator information.

    See https://wiki.anidb.net/w/UDP_API_Definition#CREATOR:_Get_Creator_Information

    :param creatorid: anidb creator id
    :type creatorid: int
    :return: a tuple (data, code). data is a dictionary with the keys:
        if code == 345:
            :message str: NO SUCH CREATOR
        if code == 245:
            :creatorid int:
            :creator_name_kanji str:
            :creator_name_transcription str:
            :type int:
            :pic_name str:
            :url_english str:
            :url_japanese str:
            :wiki_url_english str:
            :wiki_url_japanese str:
            :last_update_date int:
    :rtype: EndpointResult
    """
    command = "CREATOR"

    def cb(code: int, response: str) -> Optional[EndpointDict]:
        if code == 345:
            return dict(message=response_message[code])
        if code == 245:
            parts = response.splitlines()[1].split("|")
            result = {
                "creatorid": int(parts[0]),
                "creator_name_kanji": parts[1],
                "creator_name_transcription": parts[2],
                "type": int(parts[3]),
                "pic_name": parts[4],
                "url_english": parts[5],
                "url_japanese": parts[6],
                "wiki_url_english": parts[7],
                "wiki_url_japanese": parts[8],
                "last_update_date": int(parts[9]),
            }
            cache.update(command, creatorid, result)
            return result
        return None

    entry = cache.restore(command, creatorid)
    if not use_cache or entry is None:
        return send(command, dict(creatorid=creatorid), cb)
    return entry, 233


def episode(
    eid: int = 0, aid: int = 0, aname: str = "", epno: str = "", use_cache: bool = True
) -> EndpointResult:
    """Retrieve episode information from server.

    See https://wiki.anidb.net/w/UDP_API_Definition#EPISODE:_Retrieve_Episode_Data

    Required parameters must be one of:
        - eid
        - aid and epno
        - aname and epno


    :param eid: anidb episode id
    :type eid: int, optional
    :param aid: anidb anime id
    :type aid: int, optional
    :param aname: anime name
    :type aname: str, optional
    :param epno: episode number. See docs for special chracter prefix.
    :type epno: int, optional
    :raises ValueError: raised if none of the parameters combinations are send.
    :return: a tuple (data, code). data is a dictionary with the keys:
        if code == 340:
            :message str: NO SUCH EPISODE
        if code == 245:
            :eid int:
            :aid int:
            :length int:
            :rating int:
            :votes int:
            :epno str:
            :eng str:
            :romaji str:
            :kanji str:
            :aired int:
            :type int:
            :episode_number int: episode number without special character
    :rtype: EndpointResult
    """
    criteria: Union[int, Dict[str, Any]]
    if eid:
        criteria = dict(eid=eid)
    elif aid and epno:
        criteria = dict(aid=aid, epno=epno)
    elif aname and epno:
        criteria = dict(aname=aname, epno=epno)
        logger.warning(
            "Searching episode by aname bypasses the cache. Consider using aid."
        )
    else:
        raise ValueError("At least one must be set: eid|aid and epno|aname and epno")

    command = "EPISODE"

    def cb(code: int, response: str) -> Optional[EndpointDict]:
        if code == 340:
            return dict(message=response_message[code])
        if code == 240:
            parts = response.splitlines()[1].split("|")
            result: Dict[str, Union[str, int]] = {
                "eid": int(parts[0]),
                "aid": int(parts[1]),
                "length": int(parts[2]),
                "rating": int(parts[3]),
                "votes": int(parts[4]),
                "epno": parts[5],
                "eng": parts[6],
                "romaji": parts[7],
                "kanji": parts[8],
                "aired": int(parts[9]),
                "type": int(parts[10]),
                "episode_number": int(parts[5][1:]),
            }

            cache.update(command, result["eid"], result)
            return result
        return None

    entry = cache.restore(command, criteria)
    if not use_cache or entry is None:
        return send(command, criteria, cb)
    return entry, 233


def updated(age: int = 0, time: int = 0, entity: int = 1) -> EndpointResult:
    """Retrieve updated anime ids since specified time.

    See https://wiki.anidb.net/w/UDP_API_Definition#UPDATED:_Get_List_of_Updated_Anime_IDs
    Exactly one of age or time must be provided.

    :param age: updated in the last `age` days
    :type age: int, optional
    :param time: updated since `time` as unix timestamp
    :type time: int, optional
    :param entity: do not modify.
    :type entity: int, optional
    :raises ValueError: raised if neither or both age and time are provided.
    :return: a tuple (data, code). data is a dictionary with the keys:
        if code == 343:
            :message str: NO UPDATES
        if code == 243:
            :entity int:
            :total_count int:
            :last_update_date int:
            :aid_list List[int]:
    :rtype: EndpointResult
    """
    if (age and time) or not (age or time):
        raise ValueError("Exactly one of age or time must be provided.")

    criteria: Dict[str, Union[str, int]] = dict(entity=entity)
    if age:
        criteria["age"] = age
    else:
        criteria["time"] = time

    def cb(code: int, response: str) -> Optional[EndpointDict]:
        if code == 343:
            return dict(message=response_message[code])
        if code == 243:
            parts = response.splitlines()[1].split("|")
            return {
                "entity": int(parts[0]),
                "total_count": int(parts[1]),
                "last_update_date": int(parts[2]),
                "aid_list": int_list(parts[3]),
            }
        return None

    return send("UPDATED", criteria, cb)


def group(gid: int = 0, gname: str = "", use_cache: bool = True) -> EndpointResult:
    """Retrieve group information from server.

    See https://wiki.anidb.net/w/UDP_API_Definition#GROUP:_Retrieve_Group_Data
    One of gid, gname must be provided.

    :param gid: anidb group id
    :type gid: int, optional
    :param gname: anidb group name or shortname
    :type gname: str, optional
    :raises ValueError: raised if neither gid or gname are provided.
    :return: a tuple (data, code). data is a dictionary with the keys:
        if code == 350:
            :message str: NO SUCH GROUP
        if code == 250:
            :gid int:
            :rating int:
            :votes int:
            :acount int:
            :fcount int:
            :name str:
            :short str:
            :irc_channel str:
            :irc_server str:
            :url str:
            :picname str:
            :foundeddate int:
            :disbandeddate int:
            :dateflags int:
            :lastreleasedate int:
            :lastactivitydate int:
            :grouprelations List[Tuple[int, int]]: list of (other group id, relation type)
    :rtype: EndpointResult
    """
    command = "GROUP"
    criteria: Dict[str, Union[str, int]] = {}
    if gid:
        criteria["gid"] = gid
    elif gname:
        criteria["gname"] = gname
    else:
        raise ValueError("Either gid or gname must be provided")

    def cb(code: int, response: str) -> Optional[EndpointDict]:
        if code == 350:
            return dict(message=response_message[code])
        if code == 250:
            parts = response.splitlines()[1].split("|")
            result: Dict[str, Any] = {
                "gid": int(parts[0]),
                "rating": int(parts[1]),
                "votes": int(parts[2]),
                "acount": int(parts[3]),
                "fcount": int(parts[4]),
                "name": parts[5],
                "short": parts[6],
                "irc_channel": parts[7],
                "irc_server": parts[8],
                "url": parts[9],
                "picname": parts[10],
                "foundeddate": int(parts[11]),
                "disbandeddate": int(parts[12]),
                "dateflags": int(parts[13]),
                "lastreleasedate": int(parts[14]),
                "lastactivitydate": int(parts[15]),
                "grouprelations": mappings.group.parse_relations(parts[16]),
            }
            return cache.update(command, result["gid"], result)
        return None

    # TODO if short name is provided, the cache doesnt work.
    entry = cache.restore(command, criteria)
    if not use_cache or entry is None:
        return send(command, criteria, cb)
    return entry, 233


def groupstatus(aid: int, state: int = 0) -> EndpointResult:
    """Retrieve anime release status for different groups.

    :param aid: anidb anime id
    :type aid: int
    :param state: release state. int 1 to 6. Example: zenchi.mappings.group_status.ONGOING
    :type state: int, optional
    :return: a tuple (data, code). data is a dictionary with the keys:
        if code == (325, 330:
            :message str: NO SUCH GROUPS FOUND, NO SUCH ANIME
        if code == 225:
            :status: List of dictionaries with the following keys:
                :group_id int:
                :group_name str:
                :completion_state int:
                :last_episode_number int:
                :rating int:
                :votes int:
                :episode_range str:
            :truncated bool: if the response was truncated because it didn't fit the UDP packet, this will be True.
    :rtype: EndpointResult
    """

    def cb(code: int, response: str) -> Optional[EndpointDict]:
        if code in (325, 330):
            return dict(message=response_message[code])
        if code == 225:
            result = []
            groups_data = response.splitlines()[1:]
            truncated = False
            for group_data in groups_data:
                parts = group_data.split("|")
                if len(parts) < 7:
                    logger.warning(
                        "Response was truncated, too much data for UDP packet."
                    )
                    truncated = True
                    break
                result.append(
                    {
                        "group_id": int(parts[0]),
                        "group_name": parts[1],
                        "completion_state": int(parts[2]),
                        "last_episode_number": int(parts[3]),
                        "rating": int(parts[4]),
                        "votes": int(parts[5]),
                        "episode_range": parts[6],
                    }
                )
            return dict(status_list=result, truncated=truncated)
        return None

    params: Dict[str, Union[str, int]] = dict(aid=aid)
    if state:
        params["state"] = state
    return send("GROUPSTATUS", params, cb)
