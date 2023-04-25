import server

import sys
sys.path.append("../")
import config

def test_dfa():
    sdfa = server.split_DFA(".a")
    print(sdfa[0])
    print(len(str(sdfa[0])))
    with open("log.txt", "w") as f:
        for i in range(config.NODE_NUM):
            f.write(f"node {i}:\n")
            f.write(f"accept state = {sdfa[i]['accept_states']}\n")
        f.write("-------------------------------------------------\n")
        for j in range(len(sdfa[i]["dfa"])):
            for i in range(config.NODE_NUM):
                f.write(f"{sdfa[i]['dfa'][j][0].hex()}: {sdfa[i]['dfa'][j][1].hex()}\t")
            f.write("\n")