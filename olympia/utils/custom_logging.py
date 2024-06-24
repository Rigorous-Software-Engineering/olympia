import logging

BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[33m"
RESET = "\033[0m"

logger = logging.getLogger("olympia")
logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s', level=logging.DEBUG)