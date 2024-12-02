import socket

from mocket import (
    Mocket,
    MocketBytesEntry,
    MocketBytesRequest,
    MocketBytesResponse,
    mocketize,
)


@mocketize
def test_bytes_register_response() -> None:
    # arrange
    address = ("example.com", 5000)

    MocketBytesEntry.register_response(
        address=address,
        response=MocketBytesResponse(b"test-response"),
    )

    # act
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(address)
    sock.sendall(b"test-request")
    response_data = sock.recv(4096)
    sock.close()

    # assert
    assert response_data == b"test-response"

    requests = Mocket.request_list()
    assert len(requests) == 1
    assert type(requests[0]) is MocketBytesRequest
    assert requests[0].data == b"test-request"


@mocketize
def test_bytes_register_responses() -> None:
    # arrange
    address = ("example.com", 5000)

    MocketBytesEntry.register_responses(
        address=address,
        responses=[
            MocketBytesResponse(b"test-response-1"),
            MocketBytesResponse(b"test-response-2"),
            MocketBytesResponse(b"test-response-3"),
        ],
    )

    # act
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(address)
    sock.sendall(b"test-request-1")
    response_data_1 = sock.recv(4096)
    sock.sendall(b"test-request-2")
    response_data_2 = sock.recv(4096)
    sock.sendall(b"test-request-3")
    response_data_3 = sock.recv(4096)
    sock.close()

    # assert
    assert response_data_1 == b"test-response-1"
    assert response_data_2 == b"test-response-2"
    assert response_data_3 == b"test-response-3"

    requests = Mocket.request_list()
    assert len(requests) == 3
    assert type(requests[0]) is MocketBytesRequest
    assert type(requests[1]) is MocketBytesRequest
    assert type(requests[2]) is MocketBytesRequest
    assert requests[0].data == b"test-request-1"
    assert requests[1].data == b"test-request-2"
    assert requests[2].data == b"test-request-3"
