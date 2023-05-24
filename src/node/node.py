import util
import time
from Crypto.Cipher import AES
from typing import Sequence, Tuple
from tqdm import tqdm

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

    def __send_and_intermediate(self, xi: bytes, yi: bytes) -> Tuple[bytes, bytes]:
        req = proto.node_notify()
        req.key = self.__key
        req.turn = self.__turn
        req.xa = xi
        req.yb = yi
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
        return res.xa, res.yb

    def __share_and(self, xi: bytes, yi: bytes) -> bytes:
        self.__and_count += 1

        l = len(xi)
        assert l == len(yi), f"{l} != {len(yi)}"
        ai, bi, ci = self.__get_tripple(l)
        xi_ai = util.XOR(xi, ai)
        yi_bi = util.XOR(yi, bi)
        xa, yb = self.__send_and_intermediate(xi_ai, yi_bi)

        result = bytearray(ci)
        if self.__idx == 0:
            util.XOR_ba_b(result, util.AND(xa, yb))
        util.XOR_ba_b(result, util.AND(bi, xa))
        util.XOR_ba_b(result, util.AND(ai, yb))
        self.__turn += 1
        return bytes(result)

    def __share_1_byte_and(self, xib: bytes) -> int:
        self.__and_count += 3

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
            xa, yb = self.__send_and_intermediate(xi_ai.to_bytes(1, byteorder="big"), yi_bi.to_bytes(1, byteorder="big"))
            xa, yb = int.from_bytes(xa, byteorder="big"), int.from_bytes(yb, byteorder="big")

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
                right = cmp[l//2:l]
                cmp = self.__share_and(left, right) + cmp[l:]
        # NAND cmp bits
        return self.__share_1_byte_and(cmp)

    def __share_1_byte_and_group(self, xib: Sequence[bytes]) -> int:
        self.__and_count += 3

        assert len(xib[0]) == 1
        ai_t, bi_t, ci_t = self.__get_tripple(len(xib))
        xib = [x[0] for x in xib]

        def is_zero(x: Sequence):
            for i in x:
                if i != 0:
                    return False
            return True

        for l in [4, 2, 1]:
            mask = ((1 << l) - 1)
            ai = [c & mask for c in ai_t]
            bi = [c & mask for c in bi_t]
            ci = [c & mask for c in ci_t]
            yi = [c & mask for c in xib] # LSB, right
            xi = [(c & (mask << l)) >> l for c in xib] # MSB, left

            xi_ai = [a ^ b for a, b in zip(xi, ai)]
            yi_bi = [a ^ b for a, b in zip(yi, bi)]
            xa, yb = self.__send_and_intermediate(bytes(xi_ai), bytes(yi_bi))

            xib = list(ci)
            if self.__idx == 0:
                xib = [a ^ (b & c) for a, b, c in zip(xib, xa, yb)]
            xib = [a ^ (b & c) for a, b, c in zip(xib, bi, xa)]
            xib = [a ^ (b & c) for a, b, c in zip(xib, ai, yb)]

            ai_t = [x >> l for x in ai_t]
            bi_t = [x >> l for x in bi_t]
            ci_t = [x >> l for x in ci_t]
            assert is_zero([x & (~mask) for x in xib]), f"{xib} {hex(mask)}"

            self.__turn += 1
        return xib

    def __share_compare_group(self, xi: Sequence[bytes], yi: Sequence[bytes]):
        assert len(xi) == len(yi)
        zi = [self.__share_not(util.XOR(x, y)) for x, y in zip(xi, yi)]

        l = len(zi[0])
        while l > 1:
            if l % 2 == 0:
                l //= 2
                zli = [z[:l] for z in zi]
                zlim = b''.join(zli)
                zri = [z[l:] for z in zi]
                zrim = b''.join(zri)

                cmp = self.__share_and(zlim, zrim)
                assert len(cmp) == l * len(zi)

                zi = [cmp[i*l:(i+1)*l] for i in range(len(zi))]
            else:
                l = (l - 1) // 2
                zli = [z[:l] for z in zi]
                zlim = b''.join(zli)
                zri = [z[l:] for z in zi]
                zrim = b''.join(zri)

                cmp = self.__share_and(zlim, zrim)
                assert len(cmp) == l * len(zi)

                zi = [cmp[i*l:(i+1)*l] + zi[2*l:] for i in range(len(zi))]
            l = len(zi[0])
        return self.__share_1_byte_and_group(zi)

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

        self.__and_count = 0
    
    def gen_tripple(self, aes_key: bytes, aes_iv: bytes, l: int = 0, c: bytes = b""):
        aes = AES.new(key=aes_key, mode=AES.MODE_OFB, iv=aes_iv)
        if c == b"":
            res = aes.encrypt(b"\0" * (3 * l))
            self.set_tripple(res[:l], res[l:2*l], res[2*l:3*l])
        else:
            l = len(c)
            res = aes.encrypt(b"\0" * (2 * l))
            self.set_tripple(res[:l], res[l:], c)

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
        sigma = len(self.__dfa["inputs"]) + 1
        state_len = len(self.__dfa["dfa"][0][0])
        curr_state = b"\0" * state_len
        Q_sigma = Q * sigma
        print(f"Q_sigma = {Q_sigma}, state_len = {state_len}")
        dfa_value = b""
        for i in range(sigma):
            for j in range(Q):
                dfa_value += self.__dfa["dfa"][i][j]
        assert len(dfa_value) == Q_sigma * state_len, f"dfa_value length wrong"
        
        # for round, i in enumerate(input):
        for i in tqdm(input):
            # before = len(self.__ai)
            # print(f"evaluating input {round}")
            curr_input = i.to_bytes(1, byteorder="big")
            mask = b""
            mask_a = [[0] * Q for _ in range(sigma)]
            mask_b = [[0] * Q for _ in range(sigma)]

            cmp_list1 = []
            cmp_list2 = []
            for j in range(Q):
                cmp_list1.append(curr_state)
                cmp_list2.append(self.__dfa["states"][j])
            for i in range(sigma-1):
                cmp_list1.append(curr_input)
                cmp_list2.append(self.__dfa["inputs"][i])
            
            res_list = self.__share_compare_group(cmp_list1, cmp_list2)
            assert len(res_list) == len(cmp_list1)
            k = 0
            for j in range(Q):
                res = res_list[k]
                k += 1
                for i in range(sigma):
                    mask_a[i][j] = res
            res_ignore = 1 if self.__idx == 0 else 0
            for i in range(sigma-1):
                res = res_list[k]
                res_ignore ^= res
                k += 1
                for j in range(Q):
                    mask_b[i][j] = res
            for j in range(Q):
                mask_b[-1][j] = res_ignore

            
            x = util.arr2d_2_num(mask_a).to_bytes(Q_sigma // 8 + 1, byteorder="big")
            y = util.arr2d_2_num(mask_b).to_bytes(Q_sigma // 8 + 1, byteorder="big")
            z = self.__share_and(x, y)
            mask_r = util.num_2_arr2d(int.from_bytes(z, byteorder="big"), sigma, Q)
            for i in range(sigma):
                for j in range(Q):
                    mask += self.__gen_mask(mask_r[i][j], state_len)

            assert len(mask) == Q_sigma * state_len, f"mask length wrong, len(mask) = {len(mask)}"
            # print(f"round {round} get mask")
            now = len(self.__ai)
            # print(f"[beaver] stage 1 consume {before - now} beaver.")
            # before = now
            lres = self.__share_and(mask, dfa_value)
            now = len(self.__ai)
            # print(f"[beaver] stage 2 consume {before - now} beaver.")

            res = bytearray(lres[:state_len])
            assert len(lres) % state_len == 0
            for j in range(state_len, len(lres), state_len):
                util.XOR_ba_b(res, lres[j:j+state_len])
            
            curr_state = bytes(res)
            # print(f"round {round} finish, curr_state = {curr_state.hex()}")
        
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
        req.ParseFromString(data)
        node.set_key(req.key)
        
        if req.mode == proto.node_request.PLAIN:
            node.gen_tripple(req.aes_key, req.aes_iv, c = req.ci)
        else:
            node.gen_tripple(req.aes_key, req.aes_iv, l = req.length)
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

