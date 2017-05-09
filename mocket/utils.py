def create_sock_pair(socket_class, socket_module):
    """
        socket.socketpair() emulation
    """
    # Create a temporary server socket
    temp_srv_sock = socket_class(socket_module.AF_UNIX, socket_module.SOCK_STREAM)
    temp_srv_sock.bind('/tmp/mocket.sock')
    sockname = temp_srv_sock.getsockname()
    temp_srv_sock.listen()

    # Create a client socket
    client_sock = socket_class(socket_module.AF_UNIX, socket_module.SOCK_STREAM)

    client_sock.connect(sockname)

    fd, _ = temp_srv_sock._accept()

    srv_sock = socket_class(
        temp_srv_sock.family,
        temp_srv_sock.type,
        fileno=fd,
    )

    return client_sock, srv_sock
