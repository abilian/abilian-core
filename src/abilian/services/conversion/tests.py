import os
import sys
import tempfile
from pathlib import Path
from typing import Iterator, Union
from warnings import warn

from magic import Magic
from pytest import fixture, mark

from abilian.services.conversion.handlers import HAS_LIBREOFFICE, HAS_PDFTOTEXT
from abilian.services.conversion.service import Converter

mime_sniffer = Magic(mime=True)
encoding_sniffer = Magic(mime_encoding=True)

# FIXME: tests that rely on OOo are disabled until we fix stability issues.


@fixture
def converter() -> Iterator[Union[Iterator, Iterator[Converter]]]:
    from abilian.services.conversion import converter as c

    cache_dir = Path(tempfile.mkdtemp(suffix="unittest"))
    tmp_dir = Path(tempfile.mkdtemp(suffix="unittest"))
    c.init_work_dirs(cache_dir, tmp_dir)
    yield c

    c.clear()


def read_file(fn: str, mode: str = "rb") -> bytes:
    return (Path(__file__).parent / "dummy_files" / fn).open(mode).read()


# To text
@mark.skipif(not HAS_PDFTOTEXT, reason="requires poppler or poppler-util")
def test_pdf_to_text(converter):
    blob = read_file("onepage.pdf")
    text = converter.to_text("", blob, "application/pdf")
    assert text


@mark.skipif(not HAS_LIBREOFFICE, reason="requires libreoffice")
def test_word_to_text(converter: Converter) -> None:
    blob = read_file("test.doc")
    text = converter.to_text("", blob, "application/msword")
    assert text


@mark.skipif(not HAS_LIBREOFFICE, reason="requires libreoffice")
def test_wordx_to_text(converter: Converter) -> None:
    blob = read_file("test.docx")
    text = converter.to_text("", blob, "application/msword")
    assert text


# def test_excel_to_text(converter):
#     blob = read_file("test.xls")
#     text = converter.to_text("", blob, "application/excel")


# To PDF
@mark.skipif(not HAS_LIBREOFFICE, reason="requires libreoffice")
def test_odt_to_pdf(converter: Converter) -> None:
    blob = read_file("test.odt")
    pdf = converter.to_pdf("", blob, "application/vnd.oasis.opendocument.text")
    assert "application/pdf" == mime_sniffer.from_buffer(pdf)


@mark.skipif(not HAS_LIBREOFFICE, reason="requires libreoffice")
def test_word_to_pdf(converter: Converter) -> None:
    blob = read_file("test.doc")
    pdf = converter.to_pdf("", blob, "application/msword")
    assert "application/pdf" == mime_sniffer.from_buffer(pdf)


@mark.skipif(
    sys.platform.startswith("linux"), reason="maybe bug due to ImagMagik settings"
)
def test_image_to_pdf(converter: Converter) -> None:
    blob = read_file("picture.jpg")
    pdf = converter.to_pdf("", blob, "image/jpeg")
    assert "application/pdf" == mime_sniffer.from_buffer(pdf)


# To images
@mark.skipif(not HAS_PDFTOTEXT, reason="requires poppler or poppler-util")
def test_pdf_to_images(converter: Converter) -> None:
    if not os.popen("which pdftoppm").read().strip():
        warn("pdftoppm not found, skipping test")
        return
    blob = read_file("onepage.pdf")
    image = converter.to_image("", blob, "application/pdf", 0)
    assert "image/jpeg" == mime_sniffer.from_buffer(image)


@mark.skipif(
    not HAS_PDFTOTEXT or not HAS_LIBREOFFICE, reason="requires poppler or poppler-util"
)
def test_word_to_images(converter: Converter) -> None:
    blob = read_file("test.doc")
    image = converter.to_image("", blob, "application/msword", 0)
    assert "image/jpeg" == mime_sniffer.from_buffer(image)
