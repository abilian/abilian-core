from os.path import join, dirname

from pytest import fixture

from ..image import resize, FIT, SCALE, CROP, get_size


@fixture
def orig_image():
  return open(join(dirname(__file__), "cat.jpg")).read()


def test_fit(orig_image):
  image = resize(orig_image, 500, 500, FIT)
  x, y = get_size(image)
  assert x == 500 or y == 500


def test_scale(orig_image):
  image = resize(orig_image, 500, 500, SCALE)
  assert get_size(image) == (500, 500)


def test_crop(orig_image):
  image = resize(orig_image, 500, 500, CROP)
  assert get_size(image) == (500, 500)
