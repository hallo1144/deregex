import os
import util
import threading
from typing import Union, Tuple, Sequence, Mapping

import sys
sys.path.append("../")
from protobuf import protocol_pb2 as proto
import connection
import config

def init(key: int, regex_len: int) -> Tuple[int, Sequence[proto.init_response.node]]:
    req = proto.init_request()
    req.key = key
    res = proto.init_response()
    res.ParseFromString(connection.init_request(req.SerializeToString()))

    return res.beaver_coef * 2 * regex_len, res.nodes

def gen_data(input_str: Union[bytes, str], beaver_len: int) -> Tuple[Sequence[Mapping[str, bytes]], Sequence[bytes]]:
    a, b, c = util.gen_tripple(beaver_len, node_num=config.NODE_NUM)
    if type(input_str) == str:
        input_str = input_str.encode("utf-8")
    input_strs = util.split(input_str)
    tripples = []
    for i in range(config.NODE_NUM):
        tripples.append({"a": a[i], "b": b[i], "c": c[i]})

    return tripples, input_strs

def query(nodes: Sequence[proto.init_response.node], beaver_tripples: Sequence[Mapping[str, bytes]], input_strs: Sequence[bytes], key: int):
    res_list = []
    thread_list = []
    r_lock = threading.Lock()

    def callback(d: bytes):
        res = proto.node_response()
        res.ParseFromString(d)
        r_lock.acquire()
        res_list.append(res.result)
        r_lock.release()

    for i in range(config.NODE_NUM):
        # query_node(data: bytes, node_addr: str, node_port: int, res_list: Sequence[bytes], lock: threading.Lock)
        data = proto.node_request()
        data.key = key
        data.input = input_strs[i]
        data.ai = beaver_tripples[i]["a"]
        data.bi = beaver_tripples[i]["b"]
        data.ci = beaver_tripples[i]["c"]

        t = threading.Thread(target = connection.query_node, args = (data.SerializeToString(),
                                                                     nodes[i].ip,
                                                                     nodes[i].port,
                                                                     callback))
        t.start()
        thread_list.append(t)
    
    for t in thread_list:
        t.join()
    
    print(res_list)
    res = res_list[0]
    for r in res_list[1:]:
        res ^= r
    
    return res

if __name__ == "__main__":
    input_str = config.INPUT
    key = int.from_bytes(os.urandom(4), byteorder="big")
    coef, nodes = init(key, len(input_str))
    beaver_tripples, input_strs = gen_data(input_str, 2 * len(input_str) * coef)
    # beaver_tripples, input_strs = gen_data(input_str, 100)
    res = query(nodes, beaver_tripples, input_strs, key)
    print(res)