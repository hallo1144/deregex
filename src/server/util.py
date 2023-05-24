import myre2
import math
import os
import time

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
    dfa_wrapper = myre2.DfaWrapper.getRegexDfa(regex)

    # add deny state(trap)
    trap_state = len(dfa_wrapper.states)
    state_len = int(math.log2(trap_state + 1) // 8) + 1

    sts = [0] * trap_state
    max_val = 0
    ignore_idx = 0
    for i in range(256):
        sts[dfa_wrapper.bytemap[i]] += 1
        if sts[dfa_wrapper.bytemap[i]] > max_val:
            max_val = sts[dfa_wrapper.bytemap[i]]
            ignore_idx = dfa_wrapper.bytemap[i]
    print(f"the biggest character group is {ignore_idx}, containing {max_val} chars, shrink rate = {256 / (256 - max_val): .2f}")

    dfa = []
    accept_states = []
    input_list = []
    for state in dfa_wrapper.states:
        if state.match:
            accept_states.append(state.index)
    for input_char in range(256):
        if dfa_wrapper.bytemap[input_char] == ignore_idx:
            continue
        dfa.append([])
        input_list.append(input_char)
        for state in dfa_wrapper.states:
            value = state.next[dfa_wrapper.bytemap[input_char]]
            value = value if value != -1 else trap_state
            value = value.to_bytes(state_len, "big")
            dfa[-1].append(value)
        
        # trap state
        dfa[-1].append(trap_state.to_bytes(state_len, "big"))
    sigma = len(input_list) + 1

    # state changes for ignore_idx
    dfa.append([])
    for state in dfa_wrapper.states:
        value = state.next[ignore_idx]
        value = value if value != -1 else trap_state
        value = value.to_bytes(state_len, "big")
        dfa[-1].append(value)
    dfa[-1].append(trap_state.to_bytes(state_len, "big"))
    
    state_list = list(range(trap_state + 1))

    # split dfa
    sdfa = [dict() for _ in range(node_num)]
    sdfa[0]["accept_states"] = [bytearray(s.to_bytes(state_len, "big")) for s in accept_states]

    state_list_split = [[bytearray(x.to_bytes(state_len, byteorder="big")) for x in state_list]]
    input_list_split = [[bytearray(x.to_bytes(1, byteorder="big")) for x in input_list]]
    for i in range(1, node_num):
        state_list_split.append([])
        input_list_split.append([])
        for j in range(trap_state + 1):
            state_list_split[i].append(os.urandom(state_len))
            XOR_ba_b(state_list_split[0][j], state_list_split[i][j])
        for j in range(sigma-1):
            input_list_split[i].append(os.urandom(state_len))
            XOR_ba_b(input_list_split[0][j], input_list_split[i][j])

    sdfa[0]["dfa"] = [[0] * (trap_state + 1) for _ in range(sigma)]
    sdfa[0]["states"] = state_list_split[0]
    sdfa[0]["inputs"] = input_list_split[0]
    for i in range(sigma):
        for j in range(trap_state + 1):
            sdfa[0]["dfa"][i][j] = bytearray(dfa[i][j])
    
    for i in range(1, node_num):
        sdfa[i]["accept_states"] = []
        sdfa[i]["states"] = state_list_split[i]
        sdfa[i]["inputs"] = input_list_split[i]
        for j in range(len(accept_states)):
            sdfa[i]["accept_states"].append(os.urandom(state_len))
            XOR_ba_b(sdfa[0]["accept_states"][j], sdfa[i]["accept_states"][j])
        
        sdfa[i]["dfa"] = [[0] * (trap_state + 1) for _ in range(sigma)]
        for j in range(sigma):
            for k in range(trap_state + 1):
                sdfa[i]["dfa"][j][k] = os.urandom(state_len)
                XOR_ba_b(sdfa[0]["dfa"][j][k], sdfa[i]["dfa"][j][k])

    for j in range(len(accept_states)):
        sdfa[0]["accept_states"][j] = bytes(sdfa[0]["accept_states"][j])
    for j in range(sigma):
        for k in range(trap_state + 1):
            sdfa[0]["dfa"][j][k] = bytes(sdfa[0]["dfa"][j][k])
    
    return sdfa