__all__ = ['db', 'babel', 'mail', 'audit']

# Standard extensions.
from flask.ext.mail import Mail
mail = Mail()

from flask.ext.sqlalchemy import SQLAlchemy
db = SQLAlchemy()

from flask.ext.babel import Babel
babel = Babel()

# Homegrown extensions.
from yaka.services.audit import AuditService
audit = AuditService()
