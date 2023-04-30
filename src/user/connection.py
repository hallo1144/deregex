import socket
import time

class NetworkStatistics:
    transmit_delay = 0
    inbound_bytes = 0
    outbound_bytes = 0

    def clear(self):
        self.transmit_delay = 0
        self.inbound_bytes = 0
        self.outbound_bytes = 0

ns = {}

def timing(direction):
    assert direction in ["in", "out"]
    def decorator(func):
        def wrapper(conn: socket.socket, *args):
            global ns
            now = time.time()
            res = func(conn, *args)
            transmit_delay = time.time() - now

            if conn not in ns:
                ns[conn] = NetworkStatistics()
            ns[conn].transmit_delay += transmit_delay

            if direction == "in":
                ns[conn].inbound_bytes += len(res)
            else:
                ns[conn].outbound_bytes += len(args[0])

            return res
        return wrapper
    return decorator

@timing("out")
def send_message(conn: socket.socket, data: bytes):
    assert len(data) < (1<<32)
    size = int.to_bytes(len(data), 4, byteorder="big")
    conn.sendall(size + data)

@timing("in")
def recv_message(conn: socket.socket):
    size = int.from_bytes(conn.recv(4), byteorder="big")
    received_payload = conn.recv(size)
    reamining_payload_size = size - len(received_payload)
    while reamining_payload_size != 0:
        received_payload += conn.recv(reamining_payload_size)
        reamining_payload_size = size - len(received_payload)
    return received_payload

def init_request(data: bytes, server_addr="127.0.0.1", server_port=8082):
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn.connect((server_addr, server_port))

    send_message(conn, data)
    res = recv_message(conn)
    conn.close()

    print(f"transmittion to server takes {ns[conn].transmit_delay: .2f} secs.")

    a = ns[conn].inbound_bytes
    print(f"data from server: {a} bytes | {a/1024} KB | {a/1024/1024} MB")
    a = ns[conn].outbound_bytes
    print(f"data to server: {a} bytes | {a/1024} KB | {a/1024/1024} MB")

    return res

def query_node(data: bytes, node_addr: str, node_port: int, callback: callable):
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn.connect((node_addr, node_port))
    send_message(conn, data)
    d = recv_message(conn)
    conn.close()

    print(f"transmittion to node takes {ns[conn].transmit_delay: .2f} secs.")

    a = ns[conn].inbound_bytes
    print(f"data from node: {a} bytes | {a/1024} KB | {a/1024/1024} MB")
    a = ns[conn].outbound_bytes
    print(f"data to node: {a} bytes | {a/1024} KB | {a/1024/1024} MB")

    callback(d)