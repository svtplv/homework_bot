class EnvVariableMissing(Exception):
    """Возбуждается если не доступна хотя бы одна переменная окружения."""

    pass


class ApiNotAvailable(Exception):
    """Возбуждается если не удается получить ответ от API."""

    pass
