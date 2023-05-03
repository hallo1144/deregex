import util
import sys
sys.path.append("../")
import config

def test_dfa():
    _, _, sdfa = util.split_DFA(".a")

    # print(sdfa[0]["dfa"])
    # print(len(str(sdfa[0])))
    with open("log.txt", "w") as f:
        for i in range(config.NODE_NUM):
            f.write(f"node {i}:\n")
            f.write(f"accept state = {sdfa[i]['accept_states']}\n")
        f.write("-------------------------------------------------\n")

        for j in range(256):
            for k in range(len(sdfa[0]["dfa"][0])):
                for i in range(config.NODE_NUM):
                    f.write(f"{sdfa[i]['dfa'][j][k].hex()}" + ("^" if i < config.NODE_NUM-1 else ""))
                f.write(" ")
            f.write("\n")

test_dfa()