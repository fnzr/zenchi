class APIError(ValueError):
    pass

    # def __init__(self, message):
    #    logger.error(message)
    #    super().__init__(message)


class IllegalParameterError(APIError):
    def __init__(self) -> None:
        super().__init__(
            (
                "505 ILLEGAL INPUT OR ACCESS DENIED. "
                "There was an invalid parameter in packet data."
            )
        )


class IllegalCommandError(APIError):
    def __init__(self) -> None:
        super().__init__(
            ("598 UNKNOWN COMMAND. " "The provided command does not exists.")
        )


class BannedError(APIError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"555 BANNED. {reason}")


class InvalidCredentialsError(APIError):
    def __init__(self) -> None:
        super().__init__(
            ("502 ACCESS DENIED. " "Failed authenticating. Check credentials.")
        )


class ClientOutdatedError(APIError):
    def __init__(self) -> None:
        super().__init__(("503 CLIENT VERSION OUTDATED. " "Protover too low."))


class ClientBannedError(APIError):
    def __init__(self, reason: str) -> None:
        super().__init__(
            (f"504 CLIENT BANNED. {reason} |" "(it's not you, it's me). Update me.")
        )


class InvalidSessionError(APIError):
    def __init__(self) -> None:
        super().__init__(
            (
                "506 INVALID SESSION."
                "A session is being expected but was not sent. Is the client outdated?"
            )
        )


class UnhandledResponseError(APIError):
    def __init__(self, data: str) -> None:
        super().__init__(f"The following response was not handled: {data}")
