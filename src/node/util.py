def XOR(x: bytes, y: bytes):
    return bytes(a ^ b for a, b in zip(x, y))

def AND(x: bytes, y: bytes):
    return bytes(a & b for a, b in zip(x, y))

def NOT(x: bytes):
    return bytes((~a & 0xff) for a in x)

def XOR_ba_b(a: bytearray, b: bytes):
    assert len(a) == len(b)
    for i in range(len(a)):
        a[i] ^= b[i]