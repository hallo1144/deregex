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

def arr2d_2_num(arr):
    x = len(arr)
    y = len(arr[0])
    res = 0
    for i in range(x):
        for j in range(y):
            res += arr[i][j]
            res <<= 1
    res >>= 1
    return res

def num_2_arr2d(num, x, y):
    res = [[0] * y for _ in range(x)]
    for i in range(x-1, -1, -1):
        for j in range(y-1, -1, -1):
            res[i][j] = num % 2
            num >>= 1
    return res