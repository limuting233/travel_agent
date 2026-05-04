from app.core.enums import StatusInfo


class BusinessException(Exception):
    """
    业务异常类，用于在业务逻辑中抛出特定异常
    """

    def __init__(self, status: StatusInfo):
        self.http_code = status.value[0]
        self.code = status.value[1]
        self.error_message = status.value[2]

        super().__init__( self.http_code, self.code, self.error_message)
