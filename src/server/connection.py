import socket
import pickle
import threading
import config
from typing import Tuple, Mapping
from protobuf import protocol_pb2 as proto

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

nodes = []

def serialize_dfa(dfa):
    return pickle.dumps(dfa)

def init_node_connection(sdfa):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    s.bind(("0.0.0.0", config.NODE_SERVER_PORT))
    s.listen(config.NODE_NUM)

    global nodes
    for i in range(config.NODE_NUM):
        conn, addr = s.accept()
        print('node_port connected by ' + str(addr))
        res = proto.node_register_response()
        res.index = i
        res.dfa = serialize_dfa(sdfa[i])
        send_message(conn, res.SerializeToString())
        nodes.append(conn)

def recv_node_notify(node: socket.socket) -> Tuple[int, int, bytes, bytes]:
    data = recv_message(node)
    res = proto.node_notify()
    res.ParseFromString(data)

    return res.key, res.turn, res.xa, res.yb

def respond_node_notify(node: socket.socket, success: bool) -> None:
    res = proto.general_response()
    res.status = proto.general_response.SUCCESS if success else proto.general_response.FAIL
    send_message(node, res.SerializeToString())

def node_broadcast(key: int, turn: int, xa: bytes, yb: bytes):
    broadcast = proto.server_broadcast()
    broadcast.key = key
    broadcast.turn = turn
    broadcast.xa = xa
    broadcast.yb = yb
    data = broadcast.SerializeToString()

    global nodes
    for node in nodes:
        send_message(node, data)

def init_request(beaver_length: int, buffer: Mapping, b_lock: threading.Lock):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    s.bind(("0.0.0.0", config.USER_SERVER_PORT))
    s.listen()

    while True:
        conn, addr = s.accept()
        print('user connected by ' + str(addr))
        data = recv_message(conn)
        req = proto.init_request()
        req.ParseFromString(data)

        key = req.key
        b_lock.acquire()
        buffer[key] = {}
        b_lock.release()

        res = proto.init_response()
        res.beaver_length = beaver_length
        
        for i in range(config.NODE_NUM):
            n = res.nodes.add()
            n.ip = config.NODE_ADDR[i]
            n.port = config.USER_NODE_PORT[i]
        
        send_message(conn, res.SerializeToString())
        conn.close()