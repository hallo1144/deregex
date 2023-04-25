import os

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