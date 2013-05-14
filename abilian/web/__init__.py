"""
This package contains various modules that should be generic and reused
in web application, specially CRM-like applications.
"""


def setup(app):
  from views import base
  app.register_blueprint(base)
