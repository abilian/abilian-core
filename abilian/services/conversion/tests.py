# coding=utf-8
from __future__ import absolute_import, print_function, unicode_literals

import tempfile
from os.path import dirname, join
from warnings import warn

import pytest
from magic import Magic, os

from abilian.services.conversion.handlers import HAS_PDFTOTEXT

BASEDIR = join(dirname(__file__), "dummy_files")

mime_sniffer = Magic(mime=True)
encoding_sniffer = Magic(mime_encoding=True)

# FIXME: tests that rely on OOo are disabled until we fix stability issues.


@pytest.yield_fixture
def converter():
    from abilian.services.conversion import converter as c

    cache_dir = tempfile.mkdtemp(suffix='unittest')
    tmp_dir = tempfile.mkdtemp(suffix='unittest')
    c.init_work_dirs(cache_dir, tmp_dir)
    yield c

    c.clear()


def read_file(fn, mode='rb'):
    return open(join(BASEDIR, fn), mode).read()


# To text
@pytest.mark.skipif(
    not HAS_PDFTOTEXT, reason="requires poppler or poppler-util")
def test_pdf_to_text(converter):
    blob = read_file("onepage.pdf")
    text = converter.to_text("", blob, "application/pdf")


def XXXtest_word_to_text(converter):
    blob = read_file("test.doc")
    text = converter.to_text("", blob, "application/msword")


def XXXtest_wordx_to_text(converter):
    blob = read_file("test.docx")
    text = converter.to_text("", blob, "application/msword")


def XXXtest_excel_to_text(converter):
    blob = read_file("test.xls")
    text = converter.to_text("", blob, "application/excel")


# To PDF
def test_odt_to_pdf(converter):
    blob = read_file("test.odt")
    pdf = converter.to_pdf("", blob, "application/vnd.oasis.opendocument.text")
    assert b"application/pdf" == mime_sniffer.from_buffer(pdf)


def test_word_to_pdf(converter):
    blob = read_file("test.doc")
    pdf = converter.to_pdf("", blob, "application/msword")
    assert b"application/pdf" == mime_sniffer.from_buffer(pdf)


def test_image_to_pdf(converter):
    blob = read_file("picture.jpg")
    pdf = converter.to_pdf("", blob, "image/jpeg")
    assert "application/pdf" == mime_sniffer.from_buffer(pdf)


# To images
@pytest.mark.skipif(
    not HAS_PDFTOTEXT, reason="requires poppler or poppler-util")
def test_pdf_to_images(converter):
    if not os.popen("which pdftoppm").read().strip():
        warn("pdftoppm not found, skipping test")
        return
    blob = read_file("onepage.pdf")
    image = converter.to_image("", blob, "application/pdf", 0)
    assert "image/jpeg" == mime_sniffer.from_buffer(image)


def test_word_to_images(converter):
    blob = read_file("test.doc")
    image = converter.to_image("", blob, "application/msword", 0)
    assert b"image/jpeg" == mime_sniffer.from_buffer(image)
