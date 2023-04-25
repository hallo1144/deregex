import pickle
import socket
from typing import Tuple

def send_message(conn: socket.socket, data: bytes) -> None:
    assert len(data) < (1<<32)
    size = int.to_bytes(len(data), 4, byteorder="big")
    conn.sendall(size + data)

def recv_message(conn: socket.socket):
    size = int.from_bytes(conn.recv(4), byteorder="big")
    received_payload = conn.recv(size)
    reamining_payload_size = size - len(received_payload)
    while reamining_payload_size != 0:
        received_payload += conn.recv(reamining_payload_size)
        reamining_payload_size = size - len(received_payload)
    return received_payload

def deserialize_dfa(dfa_str: bytes):
    return pickle.loads(dfa_str)

def node_register(server_addr: str, server_port: int) -> Tuple[socket.socket, bytes]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((server_addr, server_port))

    data = recv_message(sock)
    return sock, data

def handle_request(node_port: int) -> socket.socket:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", node_port))
    s.listen()

    while True:
        conn, addr = s.accept()
        print('user connected by ' + str(addr))
        yield conn
        conn.close()