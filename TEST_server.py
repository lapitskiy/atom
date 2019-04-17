from __future__ import print_function

from random import randint
import time
import zmq
import sys
import threading

from cl_thread import *

def main():
    server = ServerTask(node)
    server.start()

if __name__ == "__main__":
    main()
