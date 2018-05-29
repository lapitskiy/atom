#
#  Lazy Pirate server
#  Binds REQ socket to tcp://*:5555
#  Like hwserver except:
#   - echoes request as-is
#   - randomly runs slowly, or exits to simulate a crash.
#
#   Author: Daniel Lundin <dln(at)eintr(dot)org>
#
from __future__ import print_function

from random import randint
import time
import zmq
import sys
from cl_node import *

print(sys.getdefaultencoding())

node = Node()
context = zmq.Context(1)
server = context.socket(zmq.REP)
server.bind("tcp://*:5555")

cycles = 0
while True:
    request_clear = server.recv()
    request = eval(request_clear.decode())
    result_print = 'none'
    if 'wtf' in request:
        result_print = 'wtf'

    if 'addmeplz' in request:
        result = node.add_new_node(request['msg'])
        result_print = result

    if 'getnextplz' in request:
        directory = 'chain/config/'
        filename = 'node_vector.atm'
        result = node.read_dict_file(directory,filename)
        next_key = result[1][len(result[1])]['next_key']
        result_print = 'next key: '+ str(next_key)

    cycles += 1
    # Simulate various problems, after a few cycles
    if cycles > 1000 and randint(0, 1000) == 0:
        print("I: Simulating a crash")
        break
    elif cycles > 1000 and randint(0, 100) == 0:
        print("I: Simulating CPU overload")
        time.sleep(2)

    #time.sleep(1) # Do some heavy work
    send_hash = node.thishash(request_clear).encode()
    send_rep = {
            'send_hash' : send_hash,
            'msg': result
        }
    print(result_print)
    server.send(str(send_rep).encode())

server.close()
context.term()