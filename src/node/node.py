import util
import time
from tqdm import trange

import sys
sys.path.append("../")
import config
import connection
from protobuf import protocol_pb2 as proto

def print_timing(func):
    def wrapper(*args, **kwargs):
        now = time.time()
        res = func(*args, **kwargs)
        print(f"{time.time() - now: .2f} secs used.")
        return res
    return wrapper

class Node:
    def __init__(self, server_addr="127.0.0.1", server_port=8081):
        self.__sock, data = connection.node_register(server_addr, server_port)
        res = proto.node_register_response()
        res.ParseFromString(data)
        self.__idx = res.index
        self.port = config.USER_NODE_PORT[self.__idx]
        self.__dfa = connection.deserialize_dfa(res.dfa)
        print(f"node {self.__idx} create")

        self.__ai = b""
        self.__bi = b""
        self.__ci = b""
        self.__turn = 0
        self.__key = -1

        self.__and_count = 0

    def __share_and(self, xi: bytes, yi: bytes) -> bytes:
        self.__and_count += 1

        l = len(xi)
        assert l == len(yi), f"{l} != {len(yi)}"
        ai, bi, ci = self.__get_tripple(l)
        xi_ai = util.XOR(xi, ai)
        yi_bi = util.XOR(yi, bi)
        
        req = proto.node_notify()
        req.key = self.__key
        req.turn = self.__turn
        req.xa = xi_ai
        req.yb = yi_bi
        success = False
        while not success:
            connection.send_message(self.__sock, req.SerializeToString())

            data = connection.recv_message(self.__sock)
            res = proto.general_response()
            res.ParseFromString(data)
            if res.status == proto.general_response.SUCCESS:
                break
            else:
                print(f"key {self.__key} turn {self.__turn} notify fail")
                time.sleep(0.05)
        
        data = connection.recv_message(self.__sock)
        res = proto.server_broadcast()
        res.ParseFromString(data)
        assert res.key == self.__key and res.turn == self.__turn
        xa, yb = res.xa, res.yb

        result = bytearray(ci)
        if self.__idx == 0:
            util.XOR_ba_b(result, util.AND(xa, yb))
        util.XOR_ba_b(result, util.AND(bi, xa))
        util.XOR_ba_b(result, util.AND(ai, yb))
        self.__turn += 1
        return bytes(result)

    def __share_1_byte_and(self, xib: bytes) -> int:
        self.__and_count += 1

        assert len(xib) == 1
        ai_t, bi_t, ci_t = self.__get_tripple(1)
        ai_t = int.from_bytes(ai_t, byteorder="big")
        bi_t = int.from_bytes(bi_t, byteorder="big")
        ci_t = int.from_bytes(ci_t, byteorder="big")
        xib = int.from_bytes(xib, byteorder="big")
        for l in [4, 2, 1]:
            mask = ((1 << l) - 1)
            ai = ai_t & mask
            bi = bi_t & mask
            ci = ci_t & mask
            yi = xib & mask # LSB, right
            xi = (xib & (mask << l)) >> l # MSB, left

            xi_ai = xi ^ ai
            yi_bi = yi ^ bi
            
            req = proto.node_notify()
            req.key = self.__key
            req.turn = self.__turn
            req.xa = xi_ai.to_bytes(1, byteorder="big")
            req.yb = yi_bi.to_bytes(1, byteorder="big")
            success = False
            while not success:
                connection.send_message(self.__sock, req.SerializeToString())

                data = connection.recv_message(self.__sock)
                res = proto.general_response()
                res.ParseFromString(data)
                if res.status == proto.general_response.SUCCESS:
                    break
                else:
                    print(f"key {self.__key} turn {self.__turn} notify fail")
                    time.sleep(0.05)
            
            data = connection.recv_message(self.__sock)
            res = proto.server_broadcast()
            res.ParseFromString(data)
            assert res.key == self.__key and res.turn == self.__turn
            xa, yb = int.from_bytes(res.xa, byteorder="big"), int.from_bytes(res.yb, byteorder="big")

            xib = ci
            if self.__idx == 0:
                xib ^= xa & yb
            xib ^= bi & xa
            xib ^= ai & yb

            ai_t = ai_t >> l
            bi_t = bi_t >> l
            ci_t = ci_t >> l
            assert xib & (~mask) == 0, f"{hex(xib)} {hex(mask)}"

            self.__turn += 1
        return xib

    def __share_not(self, xi):
        if self.__idx == 0:
            return util.NOT(xi)
        else:
            return xi

    def __share_compare(self, xi: bytes, yi: bytes) -> int:
        # xor -> nor: so NOT cmp -> AND bits
        cmp = util.XOR(xi, yi)
        cmp = self.__share_not(cmp)
        while len(cmp) > 1:
            l = len(cmp)
            if l % 2 == 0:
                left = cmp[:l//2]
                right = cmp[l//2:]
                cmp = self.__share_and(left, right)
            else:
                l -= 1
                left = cmp[:l//2]
                right = cmp[l//2:l]
                cmp = self.__share_and(left, right) + cmp[l:]
        # NAND cmp bits
        return self.__share_1_byte_and(cmp)
    
    def __gen_mask(self, x: int, mask_length: int) -> bytes:
        assert x <= 1
        if x == 0:
            return b"\0" * mask_length
        else:
            return b"\xff" * mask_length

    def set_key(self, key: int):
        self.__key = key
        self.__turn = 0

    def set_tripple(self, ai: bytes, bi: bytes, ci: bytes):
        assert len(ai) == len(bi) and len(ci) == len(bi)
        self.__ai = ai
        self.__bi = bi
        self.__ci = ci
    
    def __get_tripple(self, l: int):
        assert l < len(self.__ai)
        a = self.__ai[:l]
        self.__ai = self.__ai[l:]
        b = self.__bi[:l]
        self.__bi = self.__bi[l:]
        c = self.__ci[:l]
        self.__ci = self.__ci[l:]
        return a, b, c

    def clear_tripple(self):
        self.__ai = b""
        self.__bi = b""
        self.__ci = b""

    @print_timing
    def evaluate(self, input: bytes) -> bytes:
        connection.ns[self.__sock].clear()
        self.__and_count = 0

        Q = len(self.__dfa["states"])
        state_len = len(self.__dfa["dfa"][0][0])
        curr_state = b"\0" * state_len
        Q_sigma = Q * 256
        print(f"Q_sigma = {Q_sigma}, state_len = {state_len}")
        
        for round, i in enumerate(input):
            before = len(self.__ai)
            print(f"evaluating input {round}")
            curr_input = i.to_bytes(1, byteorder="big")
            mask_a = [[0] * Q for _ in range(256)]
            mask_b = [[0] * Q for _ in range(256)]

            for j in range(Q):
                res = self.__share_compare(curr_state, self.__dfa["states"][j])
                for i in range(256):
                    mask_a[i][j] = res
            for i in range(256):
                res = self.__share_compare(curr_input, self.__dfa["inputs"][i])
                for j in range(Q):
                    mask_b[i][j] = res
            x = util.arr2d_2_num(mask_a).to_bytes((256 * Q) // 8 + 1, byteorder="big")
            y = util.arr2d_2_num(mask_b).to_bytes((256 * Q) // 8 + 1, byteorder="big")
            z = self.__share_and(x, y)
            mask_r = util.num_2_arr2d(int.from_bytes(z, byteorder="big"), 256, Q)

            res = bytearray(b"\0" * state_len)
            for i in range(256):
                for j in range(Q):
                    mask = self.__gen_mask(mask_r[i][j], state_len)
                    lres = self.__share_and(mask, self.__dfa["dfa"][i][j])
                    util.XOR_ba_b(res, lres)
            
            now = len(self.__ai)
            print(f"[beaver] used {before - now} beaver, each round {(before - now) // Q_sigma}.")
            
            curr_state = bytes(res)
            print(f"round {round} finish, curr_state = {curr_state}")
        
        res = 0
        # OR all result: NOT -> AND -> NOT
        for ac in self.__dfa["accept_states"]:
            cmp = self.__share_compare(curr_state, ac)
            res ^= cmp
            print(f"res cmp: {cmp}")
        print(f"{len(self.__ai)} beaver tripple remains")
        print(f"transmittion to server takes {connection.ns[self.__sock].transmit_delay: .2f} secs.")

        a = connection.ns[self.__sock].inbound_bytes
        print(f"data from server: {a} bytes | {a/1024} KB | {a/1024/1024} MB")
        a = connection.ns[self.__sock].outbound_bytes
        print(f"data to server: {a} bytes | {a/1024} KB | {a/1024/1024} MB")

        print(f"AND operations: {self.__and_count} times")
        return res


if __name__ == "__main__":
    node = Node(server_addr=config.SERVER_ADDR, server_port=config.NODE_SERVER_PORT)
    for conn in connection.handle_request(node.port):
        # get_node_request
        data = connection.recv_message(conn)
        req = proto.node_request()
        try:
            req.ParseFromString(data)
        except:
            print("data length:", len(data))
            exit(1)
        node.set_key(req.key)
        node.set_tripple(req.ai, req.bi, req.ci)
        res = node.evaluate(req.input)

        # send_node_response
        resp = proto.node_response()
        resp.result = res
        connection.send_message(conn, resp.SerializeToString())

        print(f"transmittion to user takes {connection.ns[conn].transmit_delay: .2f} secs.")

        a = connection.ns[conn].inbound_bytes
        print(f"data from user: {a} bytes | {a/1024} KB | {a/1024/1024} MB")
        a = connection.ns[conn].outbound_bytes
        print(f"data to user: {a} bytes | {a/1024} KB | {a/1024/1024} MB")

