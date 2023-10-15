class EnvVariableMissing(Exception):
    """Возбуждается если не доступна хотя бы одна переменная окружения."""

    pass


class ApiNotAvailable(Exception):
    """Возбуждается если не удается получить ответ от API."""

    pass


class ResponseValidationError(Exception):
    """Возбуждается при несоответствии ответа с документацией API."""

    pass


class HomeWorkVerdictError(Exception):
    """Возбуждается при несоответствии вердикта с документацией API."""

    pass
