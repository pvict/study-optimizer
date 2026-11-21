"""Fronteira para fragments/dialogs, que o Streamlit executa separadamente."""
from functools import wraps
import os


def cloud_boundary(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        if os.environ.get('OSLER_CLOUD') == '1':
            from .cloud_ui import protected_run
            return protected_run(lambda: function(*args, **kwargs))
        return function(*args, **kwargs)
    return wrapped
