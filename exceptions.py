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