from __future__ import absolute_import, print_function, unicode_literals

from os.path import dirname, join

from pytest import fixture

from ..image import CROP, FIT, SCALE, get_save_format, get_size, resize


@fixture
def orig_image():
    # 725x518
    return open(join(dirname(__file__), "cat.jpg")).read()


def test_get_save_format():
    assert get_save_format('JPG') == 'JPEG'
    assert get_save_format('JPEG') == 'JPEG'
    assert get_save_format('PNG') == 'PNG'
    assert get_save_format('GIF') == 'PNG'
    assert get_save_format('unknown') == 'JPEG'


def test_fit(orig_image):
    image = resize(orig_image, 500, 500, FIT)
    x, y = get_size(image)
    assert (x, y) == (500, 357)

    # image already fits in desired dimension
    image = resize(orig_image, 1000, 1000, FIT)
    x, y = get_size(image)
    assert x == 725 and y == 518


def test_scale(orig_image):
    image = resize(orig_image, 500, 500, SCALE)
    assert get_size(image) == (500, 500)


def test_crop(orig_image):
    image = resize(orig_image, 500, 500, CROP)
    assert get_size(image) == (500, 500)
