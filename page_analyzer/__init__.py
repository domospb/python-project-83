# Import routes to register them with the app
from . import routes  # noqa: F401
from .app import app

__all__ = ['app']
