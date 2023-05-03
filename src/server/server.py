import math
import threading
import util

import sys
sys.path.append("../")
import config
import connection

buffer = {}
b_lock = threading.Lock()

def node_listen(node):
    while True:
        key, turn, xa, yb = connection.recv_node_notify(node)

        b_lock.acquire()
        if key not in buffer:
            b_lock.release()
            connection.respond_node_notify(node, success=False)
            return
        connection.respond_node_notify(node, success=True)
        
        if turn not in buffer[key]:
            buffer[key][turn] = {}
            buffer[key][turn]["xa"] = bytearray(xa)
            buffer[key][turn]["yb"] = bytearray(yb)
            buffer[key][turn]["counter"] = 1
        else:
            util.XOR_ba_b(buffer[key][turn]["xa"], xa)
            util.XOR_ba_b(buffer[key][turn]["yb"], yb)
            buffer[key][turn]["counter"] += 1
        
        
        if buffer[key][turn]["counter"] == config.NODE_NUM:
            xa_all = bytes(buffer[key][turn]["xa"])
            yb_all = bytes(buffer[key][turn]["yb"])
            b_lock.release()
            connection.node_broadcast(key, turn, xa_all, yb_all)
        else:
            b_lock.release()
    
threads = []
def node_receiver_start():
    global threads
    for node in connection.nodes:
        threads.append(threading.Thread(target = node_listen, args = (node,)))
        threads[-1].start()

def user_receiver_start(beaver_coef: int):
    global threads, buffer, b_lock
    threads.append(threading.Thread(target = connection.init_request, args = (beaver_coef, buffer, b_lock)))
    threads[-1].start()

def main():
    Q, Q_ac, sdfa = util.split_DFA(config.REGEX)
    Q += 1
    state_len = int(math.log2(Q + 1) // 8) + (0 if math.log2(Q + 1) % 8 == 0 else 1)
    print(f"Q: {Q}, state_len: {state_len}")

    connection.init_node_connection(sdfa)
    node_receiver_start()

    user_receiver_start(Q * (2 * state_len + 1) * config.SIGMA + state_len * Q_ac)

    global threads
    for i in range(len(threads)):
        threads[i].join()
    

if __name__ == "__main__":
    main()