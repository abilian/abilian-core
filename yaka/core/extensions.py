"""
Create all standard extensions.

Because of issues with circular dependencies, Abilian-specific extensions are
created later.
"""


__all__ = ['db', 'babel', 'mail', 'login_manager']

# Standard extensions.
from flask.ext.mail import Mail
mail = Mail()

from flask.ext.sqlalchemy import SQLAlchemy
db = SQLAlchemy()

from flask.ext.babel import Babel
babel = Babel()

from flask.ext.login import LoginManager
login_manager = LoginManager()

