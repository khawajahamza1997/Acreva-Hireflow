from app.utils.hashing import compute_file_hash


def test_identical_bytes_produce_identical_hash():
    content = b"same file content"
    assert compute_file_hash(content) == compute_file_hash(content)


def test_different_bytes_produce_different_hash():
    assert compute_file_hash(b"file one") != compute_file_hash(b"file two")


def test_hash_is_deterministic_sha256_hex():
    import hashlib

    content = b"hello world"
    assert compute_file_hash(content) == hashlib.sha256(content).hexdigest()
