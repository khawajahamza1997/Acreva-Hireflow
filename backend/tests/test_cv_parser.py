from app.services.cv_parser import extract_text_from_bytes, is_supported_filename


def test_supported_filenames():
    assert is_supported_filename("cv.pdf")
    assert is_supported_filename("CV.DOCX")
    assert is_supported_filename("resume.txt")
    assert not is_supported_filename("resume.doc")
    assert not is_supported_filename("photo.png")
    assert not is_supported_filename("archive.zip")


def test_txt_extraction():
    content = "Jane Doe\nSoftware Engineer\n5 years Python".encode("utf-8")
    assert "Jane Doe" in extract_text_from_bytes(content, "cv.txt")


def test_empty_txt_extraction_returns_empty_string():
    assert extract_text_from_bytes(b"", "cv.txt") == ""


def test_corrupted_pdf_does_not_raise():
    # Not a real PDF — extraction must fail gracefully (empty string), never crash the batch.
    garbage = b"%PDF-1.4 this is not a real pdf structure \x00\x01\x02"
    result = extract_text_from_bytes(garbage, "broken.pdf")
    assert result == ""


def test_corrupted_docx_does_not_raise():
    garbage = b"not a real docx zip file"
    result = extract_text_from_bytes(garbage, "broken.docx")
    assert result == ""


def test_unsupported_extension_returns_empty_string():
    assert extract_text_from_bytes(b"anything", "photo.png") == ""
