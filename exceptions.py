from fastapi import HTTPException, status


class ConflictHTTPException(HTTPException):
	def __init__(self, detail: str | None = "Ошибка при создании ресурса."):
		super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class UnauthorizedHTTPException(HTTPException):
	def __init__(self, detail: str | None = "Ошибка при авторизации."):
		super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class NotFoundHTTPException(HTTPException):
	def __init__(self, detail: str | None = "Ресурс не найден."):
		super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ForbiddenHTTPException(HTTPException):
	def __init__(self, detail: str | None = "Отказано в доступе."):
		super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class UnprocessableHTTPException(HTTPException):
	def __init__(self, detail: str | None = "Ошибка при обработке."):
		super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)


class NotImplementedHTTPException(HTTPException):
	def __init__(self, detail: str | None = "Функция не имплементирована."):
		super().__init__(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=detail)


class TooManyRequestsHTTPException(HTTPException):
	def __init__(self, detail: str | None = "Слишком много попыток. Попробуйте позже."):
		super().__init__(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail)


class BadRequestHTTPException(HTTPException):
	def __init__(self, detail: str | None = "Некорректный запрос."):
		super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class UnknownHTTPException(HTTPException):
	def __init__(self, detail: str | None = "Неизвестная ошибка."):
		super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)