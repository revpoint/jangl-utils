from pykafka.exceptions import ProduceFailureError


class InvalidDataError(ProduceFailureError):
    pass


class MissingKeyError(InvalidDataError):
    pass
