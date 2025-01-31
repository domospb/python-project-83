from .app import app

# Import routes to register them with the app
from . import routes  # noqa: F401

__all__ = ['app']
