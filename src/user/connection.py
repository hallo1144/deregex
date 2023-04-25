import socket

def send_message(conn: socket.socket, data: bytes):
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

def init_request(data: bytes, server_addr="127.0.0.1", server_port=8082):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((server_addr, server_port))

    send_message(s, data)
    res = recv_message(s)
    s.close()
    return res

def query_node(data: bytes, node_addr: str, node_port: int, callback: callable):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((node_addr, node_port))
    print(f"sending, data langth = {len(data)}")
    send_message(s, data)
    d = recv_message(s)
    s.close()
    callback(d)