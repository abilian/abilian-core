"""
Provides tools (currently: only functions, not a real service) for image
processing.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from cStringIO import StringIO
from PIL import Image

import hashlib


__all__ = ['resize', 'crop_and_resize']

# TODO: cache to file
cache = {}


def get_format(img):
  if isinstance(img, basestring):
    img = StringIO(img)
  pos = img.tell()
  image = Image.open(img)
  img.seek(pos)
  return image.format


def resize(orig, hsize):
  cache_key = (hashlib.md5(orig).digest(), hsize, hsize)
  if cache_key in cache:
    return cache[cache_key]

  if isinstance(orig, basestring):
    orig = StringIO(orig)

  image = Image.open(orig)
  format = image.format
  x, y = image.size

  if x <= hsize:
    orig.seek(0)
    return orig.read()

  x1 = hsize
  y1 = int(1.0 * y * hsize / x)
  image.thumbnail((x1, y1), Image.ANTIALIAS)
  output = StringIO()

  if format in ('GIF', 'PNG'):
    image.save(output, "PNG")
  else:
    image.save(output, "JPEG")
  converted = output.getvalue()
  cache[cache_key] = converted

  return converted


def crop_and_resize(orig, hsize, vsize=0):
  if isinstance(orig, basestring):
    orig = StringIO(orig)

  if not vsize:
    vsize = hsize

  original_pos = orig.tell()
  cache_key = (hashlib.md5(orig.read()).digest(), hsize, vsize)
  orig.seek(original_pos)
  if cache_key in cache:
    return cache[cache_key]

  image = Image.open(orig)
  format = image.format

  # Compute cropping coordinates
  x1 = y1 = 0
  x2, y2 = image.size
  w_ratio = 1.0 * x2 / hsize
  h_ratio = 1.0 * y2 / vsize
  if h_ratio > w_ratio:
    y1 = int(y2 / 2 - hsize * w_ratio / 2)
    y2 = int(y2 / 2 + vsize * w_ratio / 2)
  else:
    x1 = int(x2 / 2 - hsize * h_ratio / 2)
    x2 = int(x2 / 2 + vsize * h_ratio / 2)
  image = image.crop((x1, y1, x2, y2))

  image.thumbnail((hsize, vsize), Image.ANTIALIAS)

  output = StringIO()
  if format in ('GIF', 'PNG'):
    image.save(output, "PNG")
  else:
    image.save(output, "JPEG")
  converted = output.getvalue()
  cache[cache_key] = converted

  return converted
