# Don't remove
from warnings import warn
import fix_path

from os.path import join, dirname
from unittest import TestCase
from nose.tools import eq_
from magic import Magic, os

from abilian.services.conversion import converter


BASEDIR = join(dirname(__file__), "..", "dummy_files")
BASEDIR2 = join(dirname(__file__), "..", "dummy_files2")

mime_sniffer = Magic(mime=True)
encoding_sniffer = Magic(mime_encoding=True)


# FIXME: tests that rely on OOo are disabled until we fix stability issues.

class Test(TestCase):

  @classmethod
  def tearDownClass(cls):
    converter.clear()

  def read_file(self, fn):
    try:
      return open(join(BASEDIR, fn)).read()
    except IOError, e:
      return open(join(BASEDIR2, fn)).read()

  # To text
  def test_pdf_to_text(self):
    if not os.popen("which pdftotex").read().strip():
      warn("pdftotext not found, skipping test")
      return
    blob = self.read_file("onepage.pdf")
    text = converter.to_text("", blob, "application/pdf")

  def XXXtest_word_to_text(self):
    blob = self.read_file("test.doc")
    text = converter.to_text("", blob, "application/msword")

  def XXXtest_wordx_to_text(self):
    blob = self.read_file("test.docx")
    text = converter.to_text("", blob, "application/msword")

  def XXXtest_excel_to_text(self):
    blob = self.read_file("test.xls")
    text = converter.to_text("", blob, "application/excel")

  # To PDF
  def XXXtest_odt_to_pdf(self):
    blob = self.read_file("test.odt")
    pdf = converter.to_pdf("", blob, "application/vnd.oasis.opendocument.text")
    eq_("application/pdf", mime_sniffer.from_buffer(pdf))

  def XXXtest_word_to_pdf(self):
    blob = self.read_file("test.doc")
    pdf = converter.to_pdf("", blob, "application/msword")
    eq_("application/pdf", mime_sniffer.from_buffer(pdf))

  def test_image_to_pdf(self):
    blob = self.read_file("picture.jpg")
    pdf = converter.to_pdf("", blob, "image/jpeg")
    eq_("application/pdf", mime_sniffer.from_buffer(pdf))

  # To images
  def test_pdf_to_images(self):
    if not os.popen("which pdftoppm").read().strip():
      warn("pdftoppm not found, skipping test")
      return
    blob = self.read_file("onepage.pdf")
    image = converter.to_image("", blob, "application/pdf", 0)
    eq_("image/jpeg", mime_sniffer.from_buffer(image))

  def XXXtest_word_to_images(self):
    blob = self.read_file("test.doc")
    image = converter.to_image("", blob, "application/msword", 0)
    eq_("image/jpeg", mime_sniffer.from_buffer(image))
