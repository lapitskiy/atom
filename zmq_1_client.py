#
#  Lazy Pirate client
#  Use zmq_poll to do a safe request-reply
#  To run, start lpserver and then randomly kill/restart it
#
#   Author: Daniel Lundin <dln(at)eintr(dot)org>
#
from __future__ import print_function
from cl_node import *
import zmq
import os

node = Node()
nodeinfo = node.read_system_file()  # получаем словарь из nodeinfo файла ноды
nodevector = node.read_vector_file()  #считывает vector и сразу бомбит
check_result = node.check_node_number(nodeinfo,nodevector)
print(check_result)

