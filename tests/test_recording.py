from mocket.recording import MocketRecord, MocketRecordStorage, _hash_request_fallback


def test_get_records_returns_all_records_for_address(tmp_path):
    storage = MocketRecordStorage(directory=tmp_path, namespace="recording-get-records")
    address = ("example.org", 80)
    signature = "signature"
    storage._records[address][signature] = MocketRecord(
        host=address[0],
        port=address[1],
        request=b"GET / HTTP/1.1\r\nHost: example.org\r\n\r\n",
        response=b"HTTP/1.1 200 OK\r\n\r\nok",
    )

    records = storage.get_records(address)

    assert len(records) == 1
    assert records[0].response == b"HTTP/1.1 200 OK\r\n\r\nok"


def test_put_record_updates_fallback_signature_without_saving(tmp_path):
    storage = MocketRecordStorage(
        directory=tmp_path, namespace="recording-put-record-fallback"
    )
    address = ("example.org", 80)
    request = b"GET / HTTP/1.1\r\nHost: example.org\r\n\r\n"
    fallback_signature = _hash_request_fallback(request)

    storage._records[address][fallback_signature] = MocketRecord(
        host=address[0],
        port=address[1],
        request=request,
        response=b"HTTP/1.1 200 OK\r\n\r\nold",
    )

    storage.put_record(
        address=address,
        request=request,
        response=b"HTTP/1.1 200 OK\r\n\r\nnew",
    )

    assert storage._records[address][fallback_signature].response.endswith(b"new")
    assert not storage.file.exists()
