class AccessStatusError(Exception):
    """Ошибка статуса доступа к серверу."""

    pass


class RequestError(Exception):
    """Исключение в запросе API."""

    pass


class EmptyHWList(Exception):
    """Ошибка списка ДЗ."""

    pass


class SendError(Exception):
    """Ошибка отправки сообщения."""

    pass
