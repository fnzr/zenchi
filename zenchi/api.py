"""Placeholder
"""
import socket
import logging
from functools import wraps
from time import sleep
from zenchi import cache, settings
from zenchi.lookup import anime as alookup
import zenchi.crypto as crypto
import zenchi.errors as errors

logger = logging.getLogger(__name__)

MAX_RECEIVE_SIZE = 4096
PROTOVER_PARAMETER = 3


def endpoint(f):
    """Decorator that wraps API endpoints in default behavior,
    particularly error code handling

    Args:
        f (Callable): API endpoint function to be wrapped

    Returns:
        dict: Whatever f returns.
    """
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        data = f(self, *args, **kwargs)
        logger.debug(data)
        return data

    return wrapper


def authenticated(f):
    """Wraps an API endpoint that requires authentication.

    If the user is not logged in, tries to login before calling the API.
    Does nothing if the user is already logged in.

    Args:
        f (Callable): API endpoint that requires a session

    Returns:
        dict: Whatever f returns
    """
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        if not self.session:
            raise errors.EndpointError((
                "This endpoint requires a session."
                "Call .auth() to acquire one."))
        return f(self, *args, **kwargs)

    return wrapper


class API:
    """TODO

    Raises:
        EnvironmentError: [description]

    Returns:
        [type]: [description]
    """

    def __init__(self, in_port=8000, session=''):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('', in_port))
        self.socket.connect(('api.anidb.net', 9000))
        self.encrypted_session = False
        self.session = session
        if session:
            self.encoding(settings.ENCODING)
        cache.setup()

    def send(self,
             command: str,
             args: dict,
             callback: [[int, str], dict],
             use_cache=True) -> dict:
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
            use_cache (bool): Do not try to recover response from cache and
                sends request to AniDB.
        Returns:
            dict: Whatever callback returns.
        """
        message = '&'.join([f"{key}={value}" for key, value in args.items()])
        packet = f"{command} {message}"
        logger.info("Sending %s", packet)

        if settings.USE_CACHE:
            cached_response = cache.restore(command, message)
        else:
            cached_response = None

        if cached_response is None:
            if self.encrypted_session:
                packet = crypto.encrypt(packet)
            else:
                packet = packet.encode(settings.ENCODING)

            self.socket.send(packet)
            raw_response = self.socket.recv(MAX_RECEIVE_SIZE)

            if self.encrypted_session:
                api_response = crypto.decrypt(raw_response)
            else:
                api_response = raw_response.decode(settings.ENCODING)
        else:
            logger.info("Found cached response. Last update: %s",
                        cached_response['updated'].strftime('%x, %X'))
            api_response = cached_response['response']
        logger.debug(api_response)

        code = int(api_response[:3])
        result = callback(code, api_response)
        if result is not None:
            cache.save(command, message, api_response)
            return result, code
        if code == 505:
            raise errors.IllegalParameterError
        if code == 598:
            raise errors.IllegalCommandError
        if code == 555:
            raise errors.BannedError(api_response.splitlines[1])
        if code == 502:
            raise errors.InvalidCredentialsError
        if code in (501, 506):
            logger.info("[%d] Invalid or expired session. Trying to login.",
                        code)
            self.auth(use_cache=False)
            return self.send(command, args, callback)
        if code in (600, 601, 602):
            logger.info("[%d] Server unavailable. Delaying and resending.",
                        code)
            sleep(30)
            return self.send(command, args, callback)
        if code == 604:
            logger.info("[%d] Server timeout. Delaying and resending.", code)
            sleep(5)
            return self.send(command, args, callback)
        raise errors.UnhandledResponseError(api_response)

    @endpoint
    def auth(self,
             username=None,
             password=None,
             client_name=None,
             client_version=None,
             nat=None,
             attempt=1,
             use_cache=True) -> dict:
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
            raise errors.EndpointError(
                "Could not login after 5 attempts. Giving up.")
        data = {
            "user": settings.USERNAME if username is None else username,
            "pass": settings.PASSWORD if password is None else password,
            "protover": PROTOVER_PARAMETER,
            "client": settings.CLIENT_NAME if client_name is None
            else client_name,
            "clientver": settings.CLIENT_VERSION if client_version is None
            else client_version,
            "enc": settings.ENCODING
        }
        if nat is not None:
            data["nat"] = nat

        def cb(code, response):
            if code == 503:
                raise errors.ClientOutdatedError
            if code == 504:
                reason = response.split('-')[1].strip()
                raise errors.ClientBannedError(reason)
            if code in (200, 201):
                parts = response.split(' ')
                self.session = parts[1]
                nat_info = parts[2] if nat == 1 else None
                return dict(session=self.session, nat=nat_info)

        return self.send("AUTH", data, cb)

    @endpoint
    def logout(self):
        """Logout. See https://wiki.anidb.net/w/UDP_API_Definition#LOGOUT:_Logout

        Returns:
            {
                code: int
            }
        """
        def cb(code, response):
            if code in (403, 203):
                self.session = ""
                return dict(message=response[3:].strip())

        return self.send("LOGOUT", {"s": self.session}, cb)

    @endpoint
    def encrypt(self, username=None, api_key=None, type=1):
        api_key = settings.ENCRYPT_API_KEY if api_key is None else api_key
        username = settings.USERNAME if username is None else username
        if not api_key:
            raise errors.EndpointError(
                ("Requested ENCRYPT but no api_key provided. "
                 "Set $ENCRYPT_API_KEY or pass as argument"))

        def cb(code, response):
            if code in (309, 509, 394):
                return dict(message=response[3:].strip())
            if code == 209:
                salt = response.split(' ')[1].strip()
                crypto.setup(api_key + salt)
                self.encrypted_session = True
                logger.info("Successfully registered encryption.")
                return dict(salt=salt)

        return self.send("ENCRYPT", dict(user=username, type=type), cb)

    @endpoint
    def encoding(self, name):
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
        def cb(code, response):
            if code in (519, 219):
                return dict(message=response[3:].strip())

        return self.send("ENCODING", dict(name=name), cb)

    @endpoint
    def ping(self, nat=None):
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
        def cb(code, response):
            if code == 300:
                port = int(response.split('\n')[1]) if nat else None
                return dict(port=port)

        data = dict() if nat is None else dict(nat=nat)
        return self.send("PING", data, cb)

    @endpoint
    @authenticated
    def anime(self, amask, aid=None, aname=None):
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
            raise ValueError("Either aid or aname must be provided")

        def cb(code, response):
            if code == 330:
                return dict(message=response[3:].strip())
            if code == 230:
                data = response.splitlines()[1]
                result = alookup.parse_response(amask, data)
                return result

        data = dict(s=self.session)
        if aid is not None:
            data['aid'] = aid
        else:
            data['aname'] = aname

        if amask is not None:
            data["amask"] = format(amask, 'x')
        return self.send("ANIME", data, cb)

    @endpoint
    @authenticated
    def animedesc(self, aid: int, part: int):
        def cb(code, response):
            if code in (330, 330):
                return dict(message=response[3:].strip())
            if code == 233:
                parts = response.splitlines()[1].split('|')
                return {
                    'current_part': int(parts[0]),
                    'max_parts': int(parts[1]),
                    'description': parts[2]
                }

        data = dict(aid=aid, part=part, s=self.session)
        return self.send("ANIMEDESC", data, cb)
