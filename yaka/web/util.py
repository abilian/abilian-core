"""
A few utility functions.

See https://docs.djangoproject.com/en/dev/topics/http/shortcuts/ for more ideas
of stuff to implement.
"""


def get_object_or_404(cls, *args):
  """Shorthand similar to Django's `get_object_or_404`."""

  return cls.query.filter(*args).first_or_404()
