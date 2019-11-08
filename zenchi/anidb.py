"""Placeholder
"""
import socket
import logging
from functools import wraps
from time import sleep
import os
from dotenv import load_dotenv
import cache
import lookup.anime as alookup
load_dotenv()

logger = logging.getLogger(__name__)

MAX_RECEIVE_SIZE = 4096
PROTOVER_PARAMETER = 3
ENCODING = 'UTF8'


class APIError(Exception):
    """Generic error on communication with Anidb API."""
    def __init__(self, code, message):
        msg = f"AniDB returned code [{code}]. {message}"
        logger.error(msg)
        super().__init__(msg)


def endpoint(f):
    """Decorator that wraps API endpoints in default behavior, particularly error code handling

    Args:
        f (Callable): API endpoint function to be wrapped

    Returns:
        dict: Whatever f returns.
    """
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        try:
            data = f(self, *args, **kwargs)
            logger.debug(data)
            return data
        except APIError as error:
            raise error

    return wrapper


def authenticated(f):
    """Wraps an API endpoint that requires authentication.

    If the user is not logged in, tries to login before calling the API endpoint.
    Does nothing if the user is already logged in.

    Args:
        f (Callable): API endpoint that requires a session

    Returns:
        dict: Whatever f returns
    """
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        if not self.session:
            logger.info("Session not found. Sending AUTH")
            self.auth()
        return f(self, *args, **kwargs)

    return wrapper


class API:
    """TODO

    Raises:
        EnvironmentError: [description]

    Returns:
        [type]: [description]
    """
    def __init__(self, in_port=8000, session='', skip_cache=True):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('', in_port))
        self.socket.connect(('api.anidb.net', 9000))
        self.session = session
        if session:
            self.encoding(ENCODING, skip_cache)
        cache.setup()

    def send(self,
             command: str,
             args: dict,
             callback: [[int, str], dict],
             skip_cache=False) -> dict:
        """Sends an UDP packet to endpoint and synchronously wait and reads a response.

        See https://wiki.anidb.net/w/UDP_API_Definition

        Args:
            command (str): API command. Ex: PING
            args (dict): Dicionary of arguments to be sent in the packet.
                Will be sent as string according to ENCODING.
                Ex: dict(foo=1, bar=2) => foo=1&bar=2
            callback (Callable[[int, str], dict]): Each command has its own rules for
                parsing the API response, so it receives the code and the raw response and
                returns the parsed response. This callback in defined in each endpoint.
                Do note that most errors are handled in the decorator endpoint.
            skip_cache (bool): Do not try to recover response from cache and sends request to AniDB.
        Returns:
            dict: Whatever callback returns.
        """
        message = '&'.join([f"{key}={value}" for key, value in args.items()])
        packet = f"{command} {message}"
        logger.info("Sending %s", packet)

        cached_response = None if skip_cache else cache.restore(
            command, message)
        if cached_response is None:
            self.socket.send(packet.encode(ENCODING))
            response = self.socket.recv(MAX_RECEIVE_SIZE).decode(ENCODING)
            cache.save(command, message, response)
        else:
            logger.info("Found cached response. Last update: %s",
                        cached_response['updated'].strftime('%x, %X'))
            response = cached_response['response']
        logger.debug(response)

        code = int(response[:3])
        if code == 505:
            raise APIError(code, "Invalid parameter in packet. See logs.")
        if code == 598:
            raise APIError(code, "Invalid command in packet. See logs.")
        if code == 555:
            raise APIError(code, "BANNED. See ya.")
        if code == 502:
            raise APIError(code, "Failed authenticating. Check credentials.")
        if code in (501, 506):
            logger.info("[%d] Invalid or expired session. Trying to login.",
                        code)
            self.auth()
        if code in (600, 601, 602):
            logger.info("[%d] Server unavailable. Delaying and resending.",
                        code)
            sleep(30)
            self.send(command, args, callback)
        if code == 604:
            logger.info("[%d] Server timeout. Delaying and resending.", code)
            sleep(5)
            self.send(command, args, callback)
        return callback(code, response)

    @endpoint
    def auth(self,
             username=None,
             password=None,
             client_name=None,
             client_version=None,
             nat=None,
             attempt=1,
             skip_cache=True) -> dict:
        """Obtains new session.
            See https://wiki.anidb.net/w/UDP_API_Definition#AUTH:_Authing_to_the_AnimeDB

        Args:
            username (str, optional): Defaults to $ANIDB_USERNAME.
            password (str, optional): Defaults to $ANIDB_PASSWORD.
            client_name (str, optional): Defaults to $ANIDB_CLIENTNAME.
            client_version (str, optional): Defaults to $ANIDB_CLIENTVERSION.
            nat (int, optional): Defaults to 0.
            attempt (int, optional): Used to retry authentication and preventing server flood.

        Raises:
            ValueError: Fired if max number of attempts to login was reached
                Server keeps asking to retry, but fails to deliver a session.
            APIError: Fired if client is outdated.
                Either the client is outdated or this script is.

        Returns:
            {
                code: int,
                session: str,
                nat: str or None
            }
        """
        if username is None:
            username = os.getenv("ANIDB_USERNAME")
        if password is None:
            password = os.getenv("ANIDB_PASSWORD")
        if client_name is None:
            client_name = os.getenv("ANIDB_CLIENTNAME")
        if client_version is None:
            client_version = os.getenv("ANIDB_CLIENTVERSION")
        if attempt > 5:
            raise ValueError("Could not login after 5 attempts. Giving up.")
        data = {
            "user": username,
            "pass": password,
            "protover": PROTOVER_PARAMETER,
            "client": client_name,
            "clientver": client_version,
            "enc": ENCODING
        }
        if nat is not None:
            data["nat"] = nat

        def cb(code, response):
            if code in (503, 504):
                raise APIError(
                    code,
                    "Client outdated. Update protover/client key or open a ticket."
                )
            if code in (200, 201):
                parts = response.split(' ')
                self.session = parts[1]
                nat_info = parts[2] if nat == 1 else None
            return dict(code=code, session=self.session, nat=nat_info)

        return self.send("AUTH", data, cb, skip_cache)

    @endpoint
    def logout(self, skip_cache=True):
        """Logout. See https://wiki.anidb.net/w/UDP_API_Definition#LOGOUT:_Logout

        Returns:
            {
                code: int
            }
        """
        def cb(code, _):
            if code == 403:
                logger.info(403, "Not logged in")
            if code == 203:
                logger.info(203, "Logged out")
            self.session = ""
            return dict(code=code)

        return self.send("LOGOUT", {"s": self.session}, cb, skip_cache)

    @endpoint
    def encoding(self, name, skip_cache=False):
        """Sets the encoding for the session. Used if session was restored.
        See https://wiki.anidb.net/w/UDP_API_Definition#ENCODING:_Change_Encoding_for_Session

        Args:
            name (str): Encoding name

        Raises:
            APIError: Raised if encoding is not valid

        Returns:
            {
                code: int
            }
        """
        def cb(code, _):
            if code == 519:
                raise APIError(code, f"Encoding [{name}] not supported")
            return dict(code=code)

        return self.send("ENCODING", dict(name=name), cb, skip_cache)

    @endpoint
    def ping(self, nat=None, skip_cache=True):
        """Pings the server. See https://wiki.anidb.net/w/UDP_API_Definition#PING:_Ping_Command

        Args:
            nat (int, optional): Any value here means true.

        Returns:
            {
                code: int,
                port: int | None
            }: Server response.
        """
        def cb(code, response):
            port = int(response.split('\n')[1]) if nat else None
            return dict(code=code, port=port)

        data = dict() if nat is None else dict(nat=nat)
        return self.send("PING", data, cb)

    @endpoint
    @authenticated
    def anime(self, amask, aid=None, aname=None, skip_cache=False):
        """Retrieve anime data according to aid or aname.

        See https://wiki.anidb.net/w/UDP_API_Definition#ANIME:_Retrieve_Anime_Data

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
            raise ValueError("Either aid or aname must be provided")

        def cb(code, response):
            print(response)
            data = response.splitlines()[1]
            result = alookup.parse_response(amask, data)
            result["code"] = code
            return result

        data = dict(s=self.session)
        if aid is not None:
            data['aid'] = aid
        else:
            data['aname'] = aname

        if amask is not None:
            data["amask"] = format(amask, 'x')
        return self.send("ANIME", data, cb)