import myre2
import math
import os
import pickle

def XOR_ba_b(a: bytearray, b: bytes):
    assert len(a) == len(b)
    for i in range(len(a)):
        a[i] ^= b[i]
    
def split_DFA(regex, node_num=2):
    if type(regex) is str:
        regex = regex.encode("utf-8")
    states = myre2.DfaWrapper.getRegexDfa(regex)

    # add deny state(trap)
    trap_state = len(states)
    state_len = int(math.log2(len(states) + 1) // 8) + 1

    dfa = {}
    accept_states = []
    for state in states:
        if state.match:
            accept_states.append(state.index)
    for input_char in range(256):
        for state in states:
            index = input_char.to_bytes(1, "big") + state.index.to_bytes(state_len, "big")

            value = state.next[input_char] if state.next[input_char] != -1 else trap_state
            value = value.to_bytes(state_len, "big")
            dfa[index] = value
        
        # trap state
        index = input_char.to_bytes(1, "big") + trap_state.to_bytes(state_len, "big")
        dfa[index] = trap_state.to_bytes(state_len, "big")

    sdfa = [dict() for _ in range(node_num)]
    sdfa[0]["accept_states"] = [bytearray(s.to_bytes(state_len, "big")) for s in accept_states]
    sdfa[0]["dfa"] = [[bytearray(k), bytearray(v)] for k, v in dfa.items()]

    for i in range(1, node_num):
        sdfa[i]["accept_states"] = []
        for j in range(len(accept_states)):
            sdfa[i]["accept_states"].append(os.urandom(state_len))
            XOR_ba_b(sdfa[0]["accept_states"][j], sdfa[i]["accept_states"][j])
        
        sdfa[i]["dfa"] = []
        for j in range(len(dfa)):
            sdfa[i]["dfa"].append([os.urandom(1+state_len), os.urandom(state_len)])
            XOR_ba_b(sdfa[0]["dfa"][j][0], sdfa[i]["dfa"][j][0])
            XOR_ba_b(sdfa[0]["dfa"][j][1], sdfa[i]["dfa"][j][1])
    
    for j in range(len(accept_states)):
        sdfa[0]["accept_states"][j] = bytes(sdfa[0]["accept_states"][j])
    for j in range(len(dfa)):
        sdfa[0]["dfa"][j][0] = bytes(sdfa[0]["dfa"][j][0])
        sdfa[0]["dfa"][j][1] = bytes(sdfa[0]["dfa"][j][1])
    
    # for j in range(len(dfa)):
    #     re_k = bytearray(b'\x00' * (state_len+1))
    #     re_v = bytearray(b'\x00' * state_len)
    #     for i in range(node_num):
    #         for k in range(state_len):
    #             re_k[k] ^= sdfa[i]["dfa"][j][0][k]
    #             re_v[k] ^= sdfa[i]["dfa"][j][1][k]
    #         re_k[-1] ^= sdfa[i]["dfa"][j][0][-1]
        
    #     re_k = bytes(re_k)
    #     re_v = bytes(re_v)
    #     assert re_k in dfa and dfa[re_k] == re_v
    return len(states), len(accept_states), sdfa