import os
import util
import threading
import time
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
    print(f"beaver per round: {res.beaver_length}, regex_len: {regex_len}")

    return res.beaver_length * regex_len, res.nodes

def gen_data(input_str: Union[bytes, str], beaver_len: int) -> Tuple[Sequence[Mapping[str, bytes]], Sequence[bytes]]:
    c, keys, iv = util.gen_tripple_by_AES(beaver_len, node_num=config.NODE_NUM)
    if type(input_str) == str:
        input_str = input_str.encode("utf-8")
    input_strs = util.split(input_str)

    return c, (keys, iv), input_strs

def query(nodes: Sequence[proto.init_response.node], key: int, c: bytes, 
          aes_param: Tuple[Sequence[bytes], Sequence[bytes]], input_strs: Sequence[bytes]):
    res_list = []
    thread_list = []
    r_lock = threading.Lock()

    def callback(d: bytes):
        res = proto.node_response()
        res.ParseFromString(d)
        r_lock.acquire()
        res_list.append(res.result)
        r_lock.release()

    plain_node = int.from_bytes(os.urandom(1), byteorder="big") % config.NODE_NUM
    idx = 0
    for i in range(config.NODE_NUM):
        # query_node(data: bytes, node_addr: str, node_port: int, res_list: Sequence[bytes], lock: threading.Lock)
        data = proto.node_request()
        data.key = key
        data.input = input_strs[i]

        if i == plain_node:
            data.mode = proto.node_request.PLAIN
            data.aes_key = aes_param[0][idx]
            data.aes_iv = aes_param[1][idx]
            data.ci = c
        else:
            data.mode = proto.node_request.AES
            data.aes_key = aes_param[0][idx]
            data.aes_iv = aes_param[1][idx]
            data.length = len(c)
            idx += 1

        t = threading.Thread(target = connection.query_node, args = (data.SerializeToString(),
                                                                     nodes[i].ip,
                                                                     nodes[i].port,
                                                                     callback))
        t.start()
        thread_list.append(t)
    
    for t in thread_list:
        t.join()
    
    print(f"res_list: {res_list}")
    res = res_list[0]
    for r in res_list[1:]:
        res ^= r
    
    return res

if __name__ == "__main__":
    input_str = config.INPUT
    key = int.from_bytes(os.urandom(4), byteorder="big")

    start = time.time()
    beaver_length, nodes = init(key, len(input_str))
    beaver_c, aes_param, input_strs = gen_data(input_str, beaver_length)
    print(f"length of beaver: {len(beaver_c)}")
    print(f"user work takes {time.time() - start} seconds.")
    res = query(nodes, key, beaver_c, aes_param, input_strs)
    
    assert res in [0, 1]
    print(("" if res == 1 else "not ") + "match.")
    print(f"the whole process takes {time.time() - start} seconds.")