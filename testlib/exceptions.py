# testlib/exceptions.py

class TestLibError(Exception):
    """Base exception for testlib operations"""
    pass

class RollbackError(TestLibError):
    """Raised when rollback operations fail"""
    pass

class AdapterError(TestLibError):
    """Raised when adapter operations fail"""
    pass

class ResourceNotFoundError(TestLibError):
    """Raised when a resource cannot be found"""
    pass