class APIError(ValueError):
    pass

    # def __init__(self, message):
    #    logger.error(message)
    #    super().__init__(message)


class IllegalParameterError(APIError):

    def __init__(self):
        super().__init__((
            "505 ILLEGAL INPUT OR ACCESS DENIED. "
            "There was an invalid parameter in packet data."))


class IllegalCommandError(APIError):

    def __init__(self):
        super().__init__((
            "598 UNKNOWN COMMAND. "
            "The provided command does not exists."))


class BannedError(APIError):

    def __init__(self, reason):

        super().__init__("555 BANNED. %s", reason)


class InvalidCredentialsError(APIError):

    def __init__(self):
        super().__init__((
            "502 ACCESS DENIED. "
            "Failed authenticating. Check credentials."))


class ClientOutdatedError(APIError):

    def __init__(self):
        super().__init__((
            "503 CLIENT VERSION OUTDATED. "
            "Protover too low."))


class ClientBannedError(APIError):

    def __init__(self, reason):
        super().__init__((
            "504 CLIENT BANNED. %s |"
            "(it's not you, it's me). Update me."), reason)


class UnhandledResponseError(APIError):

    def __init__(self, data):
        super().__init__("The following response was not handled:\n%s", data)


class EndpointError(ValueError):
    pass
