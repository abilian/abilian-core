
def get_object_or_404(cls, *args):
  return cls.query.filter(*args).first_or_404()
