"""Authorize.Net adapter exceptions"""


class AuthorizeNetError(Exception):
    """Base exception for Authorize.Net adapter"""
    pass


class AuthorizeNetAPIError(AuthorizeNetError):
    """Error from Authorize.Net API"""
    def __init__(self, message: str, error_code: str = None, response_code: str = None):
        self.error_code = error_code
        self.response_code = response_code
        super().__init__(message)


class AuthorizeNetConnectionError(AuthorizeNetError):
    """Connection error to Authorize.Net API"""
    pass


class AuthorizeNetValidationError(AuthorizeNetError):
    """Validation error for Authorize.Net request"""
    pass

