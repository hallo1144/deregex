import os
from Crypto.Cipher import AES

def XOR(x: bytes, y: bytes):
    return bytes(a ^ b for a, b in zip(x, y))

def XOR_ba_b(a: bytearray, b: bytes):
    assert len(a) == len(b)
    for i in range(len(a)):
        a[i] ^= b[i]

def AND(x: bytes, y: bytes):
    return bytes(a & b for a, b in zip(x, y))

def split(data: bytes, node_num: int = 2):
    l = len(data)
    ai = []
    ax = bytearray(data)
    for _ in range(node_num-1):
        ai.append(os.urandom(l))
        for j in range(l):
            ax[j] ^= ai[-1][j]
    ai.append(bytes(ax))
    return ai

def gen_tripple(l: int, node_num: int = 2):
    a = os.urandom(l)
    b = os.urandom(l)
    c = AND(a, b)

    return split(a, node_num=node_num), split(b, node_num=node_num), split(c, node_num=node_num)

def gen_tripple_by_AES(l: int, node_num: int = 2):
    a = os.urandom(l)
    b = os.urandom(l)
    c = AND(a, b)

    keys = []
    ivs = []
    an = bytearray(a)
    bn = bytearray(b)
    cn = bytearray(c)
    for _ in range(node_num-1):
        k = os.urandom(16)
        iv = os.urandom(16)
        keys.append(k)
        ivs.append(iv)
        aes = AES.new(key=k, mode=AES.MODE_OFB, iv=iv)
        res = aes.encrypt(b"\0" * (3 * l))

        ai_ = res[:l]
        bi_ = res[l:2*l]
        ci_ = res[2*l:3*l]

        XOR_ba_b(an, ai_)
        XOR_ba_b(bn, bi_)
        XOR_ba_b(cn, ci_)
    
    an = bytes(an)
    bn = bytes(bn)
    cn = bytes(cn)

    return an, bn, cn, keys, ivs