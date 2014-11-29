"""
Useful decorators for web views.
"""

from functools import wraps
from flask import request, render_template

__all__ = ['templated']


# Copy/pasted from: http://flask.pocoo.org/docs/patterns/viewdecorators/
def templated(template=None):
  """
  The idea of this decorator is that you return a dictionary with the values
  passed to the template from the view function and the template
  is automatically rendered.

  @deprecated
  """
  def decorator(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
      template_name = template
      if template_name is None:
        template_name = request.endpoint.replace('.', '/') + '.html'
      ctx = f(*args, **kwargs)
      if ctx is None:
        ctx = {}
      elif not isinstance(ctx, dict):
        return ctx
      return render_template(template_name, **ctx)
    return decorated_function
  return decorator
