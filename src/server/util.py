import myre2
import math
import os
import time
from Crypto.Random import random

def print_timing(func):
    def wrapper(*args, **kwargs):
        now = time.time()
        res = func(*args, **kwargs)
        print(f"DFA translation costs {time.time() - now: .2f} secs.")
        return res
    return wrapper

def XOR_ba_b(a: bytearray, b: bytes):
    assert len(a) == len(b)
    for i in range(len(a)):
        a[i] ^= b[i]

@print_timing
def split_DFA(regex, node_num=2):
    if type(regex) is str:
        regex = regex.encode("utf-8")
    states = myre2.DfaWrapper.getRegexDfa(regex)

    # add deny state(trap)
    trap_state = len(states)
    state_len = int(math.log2(len(states) + 1) // 8) + 1

    dfa = []
    accept_states = []
    for state in states:
        if state.match:
            accept_states.append(state.index)
    for input_char in range(256):
        dfa.append([])
        for state in states:
            value = state.next[input_char] if state.next[input_char] != -1 else trap_state
            value = value.to_bytes(state_len, "big")
            dfa[input_char].append(value)
        
        # trap state
        dfa[input_char].append(trap_state.to_bytes(state_len, "big")) 

    sdfa = [dict() for _ in range(node_num)]
    sdfa[0]["accept_states"] = [bytearray(s.to_bytes(state_len, "big")) for s in accept_states]
    
    # index = original, value = shuffled
    shuffle_state = list(range(trap_state + 1))
    # random.shuffle(shuffle_state)
    shuffle_input = list(range(256))
    # random.shuffle(shuffle_input)

    shuffle_state_split = [[bytearray(x.to_bytes(state_len, byteorder="big")) for x in shuffle_state]]
    shuffle_input_split = [[bytearray(x.to_bytes(1, byteorder="big")) for x in shuffle_input]]
    for i in range(1, node_num):
        shuffle_state_split.append([])
        shuffle_input_split.append([])
        for j in range(trap_state + 1):
            shuffle_state_split[i].append(os.urandom(state_len))
            XOR_ba_b(shuffle_state_split[0][j], shuffle_state_split[i][j])
        for j in range(256):
            shuffle_input_split[i].append(os.urandom(state_len))
            XOR_ba_b(shuffle_input_split[0][j], shuffle_input_split[i][j])

    sdfa[0]["dfa"] = [[0] * (trap_state + 1) for _ in range(256)]
    sdfa[0]["states"] = shuffle_state_split[0]
    sdfa[0]["inputs"] = shuffle_input_split[0]
    for i in range(256):
        for j in range(trap_state + 1):
            # sdfa[0]["dfa"][i][j] = bytearray(dfa[shuffle_input[i]][shuffle_state[j]])
            sdfa[0]["dfa"][i][j] = bytearray(dfa[i][j])
    
    for i in range(1, node_num):
        sdfa[i]["accept_states"] = []
        sdfa[i]["states"] = shuffle_state_split[i]
        sdfa[i]["inputs"] = shuffle_input_split[i]
        for j in range(len(accept_states)):
            sdfa[i]["accept_states"].append(os.urandom(state_len))
            XOR_ba_b(sdfa[0]["accept_states"][j], sdfa[i]["accept_states"][j])
        
        sdfa[i]["dfa"] = [[0] * (trap_state + 1) for _ in range(256)]
        for j in range(256):
            for k in range(trap_state + 1):
                sdfa[i]["dfa"][j][k] = os.urandom(state_len)
                XOR_ba_b(sdfa[0]["dfa"][j][k], sdfa[i]["dfa"][j][k])

    for j in range(len(accept_states)):
        sdfa[0]["accept_states"][j] = bytes(sdfa[0]["accept_states"][j])
    for j in range(256):
        for k in range(trap_state + 1):
            sdfa[0]["dfa"][j][k] = bytes(sdfa[0]["dfa"][j][k])
    

    return len(states), len(accept_states), sdfa