"""
Mixed repository fixture - Custom exceptions.
"""


class ValidationError(Exception):
    pass


class ProcessingError(Exception):
    pass


class DispatchError(Exception):
    pass
