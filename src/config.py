NODE_NUM = 2
SIGMA = 256
NODE_SERVER_PORT = 8081
SERVER_ADDR = "127.0.0.1"

USER_SERVER_PORT = 8082

NODE_ADDR = ["127.0.0.1", "127.0.0.1"]
USER_NODE_PORT = [8083, 8084]

# REGEX = ".*g"
# INPUT = b"agg"

# REGEX = ".*g.*"
# INPUT = b"aggeguh"

REGEX = "^https?://cas.*\.criteo\.com.*"
# INPUT = b"https://easylist.to/easylist/easylist.txt"
# INPUT = b"https://casino.uk.criteo.com/easylist/entry"
INPUT = "a" * 512