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
from cl_server import *
from wallet import *
import asyncio

import socket

import threading
import os

node = Node()
server = Server()
wallet = Wallet()

context = zmq.Context(1)
serverZMQ = context.socket(zmq.REP)
serverZMQ.bind("tcp://*:5555")





# если в файле ноды есть активация проведения транзакции, то нода ее старается провести
def test_poh_active(poh_active):
    if poh_active == True:
        #
        # открываем вектор нод, и узнаем, сколько в нрашем окружении рабочих нод и пытаемся их опросить.
        #
        path = 'chain/config/'

        filename = 'nodeinfo.atm'
        node_config = node.read_dict_file(path, filename)
        n = node_config['node']
        # если нода одна, тогда ждем просто любые транзакции и обрабатываем их
        filename = 'node_vector.atm'
        node_vector = node.read_dict_file(path,filename)
        dlina = len(node_vector[n])-1
        # если ноды две и больше, пытаемся связаться и сообщить, что вы в строю.
        if dlina == 1:
            print('вы в сети один')
        if dlina > 1:
            for key in range(1,dlina+1):
                if key == n or node_vector[n][key]['active'] == False:
                    print(key,' - Нода выключена')
                    continue
                print('Соединяюсь с node и ipport === '+ str(key) +' ==== ',node_vector[n][key]['ipport'])
                dict = {'iamalive': '1', 'msg': n}
                result = node.try_connect_to_network(dict,node_vector[n][key]['ipport'])
                if(result == 'ok'):
                    node_vector[n][key]['active'] = True
                    node_vector[n][n]['active'] = True
                    node_vector[key][n]['active'] = True
                if(result == 'no response'):
                    node_vector[n][key]['active'] = False # - то место выключает ноду, потом включить
            node.write_dict_file(node_vector,path,filename)



def make_tx_lake():
    path = 'chain/config/'
    dict = {}
    k = 0

    nodeinfo = node.nodeinfo()

    rnd_node_count = node.rnd_node_count(nodeinfo['node'])


    filename = 'txpool_leak.atm'
    if not os.path.exists(path):
        os.makedirs(path)
    with open(path + filename, 'rb') as f:
        while True:
            try:
                k += 1
                dict[k] = pickle.load(f)
            except EOFError:
                k -= 1
                break
    open(path + filename, 'w').close()
    if k > 1 and k != 0:  # транзакций больше одной
        print('-----------------------------')
        print('БОЛЬШЕ ОДНОЙ ТРАНЗАКЦИИ')
        print('-----------------------------')
        with open(path + filename, 'ab') as f:
            for i in range(1, k):
                pickle.dump(dict[i], f)

        msg_no_sign = dict[k].pop('sign')
        rnd_node = node.poh(msg_no_sign, rnd_node_count)
        verify = wallet.verify_sig(dict[k]['from_pbkey'], dict[k]['sign'], msg_no_sign)
        if verify == True:
            msg = dict[k]
            get_data = node.load_and_send(msg)
            filename = 'node_vector.atm'
            vector_file = node.read_dict_file(path, filename)

            result = node.poh_tx(msg, rnd_node_count)
            result2 = node.poh(msg, rnd_node_count)

            if result2 == nodeinfo['node']:
                ipport = 'localhost:5555'
            else:
                ipport = vector_file[nodeinfo['node']][result2]['ipport']
            print(vector_file[nodeinfo['node']][result2])
            result = {'yourtxnextbro': '1', 'msg': msg}  # сообщаем след. ноде, что ее задача
            print('-----------------------------')
            print('пытаемся связаться с ', ipport)
            print('-----------------------------')
            result = node.try_connect_to_network(result, ipport)
            print()
            if result == 'ok':
                print('there need delete tx in lake')

        if verify == False:
            print('bad sign')

    if k == 1:  # транзакций одна
        print('-----------------------------')
        print('ОДНА ТРАНЗАКЦИЯ')
        print('-----------------------------')
        msg_no_sign = {'from': dict[k]['from'], 'from_pbkey': dict[k]['from_pbkey'], 'count': dict[k]['count'],'send': dict[k]['send'],'send_komis': dict[k]['send_komis']}

        rnd_node_count = node.rnd_node_count(nodeinfo['node'])
        rnd_node = node.poh(msg_no_sign, rnd_node_count)
        verify = wallet.verify_sig(dict[k]['from_pbkey'], dict[k]['sign'], msg_no_sign)
        if verify == True:
            msg_no_sign['sign'] = dict[k]['sign']
            # send_to_all = node.send_to_all_node(rnd_node, msg_no_sign)

            msg = {
                'timestamp': time.time(),
                'from': dict[k]['from'],
                'from_pbkey': nodeinfo['send_pbkey'],
                'count': '0.000001',
                'send': nodeinfo['send_adr'],
                'send_komis': '0'}
            msg['sign'] = wallet.generate_sig(nodeinfo['send_prkey'], msg)
            msg['thishash'] = node.thishash(msg)
            get_data = node.load_and_send(msg)
            filename = 'node_vector.atm'
            vector_file = node.read_dict_file(path, filename)

            result = node.poh_tx(msg, rnd_node_count)
            result2 = node.poh(msg, rnd_node_count)

            ipport = vector_file[nodeinfo['node']][result2]['ipport']
            print(result2)
            print(vector_file[nodeinfo['node']][result2])
            result = {'yourtxnextbro': '1', 'msg': msg}  # сообщаем след. ноде, что ее задача
            print('-----------------------------')
            print('пытаемся связаться с ', ipport)
            print('-----------------------------')
            result = node.try_connect_to_network(result, ipport)
            if result == 'ok':
                print('there need delete lake')


        if verify == False:
            print('bad sign')
    if k == 0:  # озеро без рыбы, отправляем пустую транзакцию, для продолжения цепи
        print('-----------------------------')
        print('ОЗЕРО ПУСТОЕ')
        print('-----------------------------')
        time.sleep(3)
        print('No tx in lake.atm file, send blank tx')
        result = 0
        result2 = 0
        k = 0
        while True:

            msg = {
                'timestamp': time.time(),
                'from': nodeinfo['send_adr'],
                'from_pbkey': nodeinfo['send_pbkey'],
                'count': '0.000001',
                'send': nodeinfo['send_adr'],
                'send_komis': '0'}
            msg['sign'] = wallet.generate_sig(nodeinfo['send_prkey'], msg)
            msg['thishash'] = node.thishash(msg)
            result = node.poh_tx(msg, rnd_node_count)
            result2 = node.poh(msg, rnd_node_count)
            if result == nodeinfo['node'] and result2 != nodeinfo['node']:
                print('node number: ', nodeinfo['node'], '; result: ', result, '; result2: ', result2)
                break
        result_load = node.load_and_send(msg)

        vectorinfo = node.vectorinfo(nodeinfo['node'])  # вызывать еще раз, для обновления данных по файлу
        msg['descr'] = result_load
        msg['descr']['node_from'] = nodeinfo['node']
        msg['descr']['vector_hash'] = vectorinfo['nodehashvector']

        filename = 'node_vector.atm'
        vector_file = node.read_dict_file(path, filename)
        ipport = vector_file[nodeinfo['node']][result2]['ipport']
        print(result2)
        print(vector_file[nodeinfo['node']][result2])
        result = {'yourtxnextbro': '1', 'msg': msg}  # сообщаем след. ноде, что ее задача
        identity = nodeinfo['node']
        print('-----------------------------')
        print('пытаемся связаться с ',ipport)
        print('-----------------------------')
        result = node.try_connect_to_5556_dealer(identity,result,ipport)
    else:
        print('Node not active in web')

#
# получаем сообщения от других нод и обрабатываем их
#
def get_msg():
    print('Wait connection...')

    cycles = 0
    while True:
        request_clear = serverZMQ.recv()
        request = eval(request_clear.decode())
        result_print = 'none'
        if 'wtf' in request:
            result_print = 'wtf'

        if 'addmeplz' in request:
            result = node.add_new_node(request['msg'])
            send_rep(result, request_clear)
            result_print = result

        if 'iamalive' in request:
            send_rep('ok', request_clear)
            print('try to alive node:',request['msg'])
            result = node.alive(request['msg'])
            result_print = result

        if 'lookthistx' in request:
            send_rep('ok', request_clear)
            result = node.check_mempool_hash(request['msg'])
            result_print = result

        if 'yourtxnextbro' in request:
            print('yourtxnextbro: ',request)
            send_rep('ok',request_clear)
            print(request['msg']['descr'])
            vectorinfo = node.vectorinfo(request['msg']['descr']['node_from'])

            # проверка на совпадение хешей вектора от полуаетяли и у меня
            print(vectorinfo['nodehashvector'])
            print(request['msg']['descr']['vector_hash'])
            if request['msg']['descr']['vector_hash'] == vectorinfo['nodehashvector']:
                print('zmq server 253: hash vector equal')
            else:
                print('zmq server 253: hash vector NOT equal - need load verify vector')

            # проверка на количество недостающей цепочки и что я следующий
            result = node.getblockfromprevnode(request['msg'])

            print('zmq_server 264: ',result)
            if result:
                make_tx_lake()
            result_print = result

        if 'givemeplzlastblock' in request:
            print('none')


        if 'addmeplzinvector' in request:

            directory = 'chain/config/'
            filename = 'node_vector.atm'
            result = node.read_dict_file(directory, filename)
            send_rep(result, request_clear)

        cycles += 1
        # Simulate various problems, after a few cycles
        if cycles > 1000 and randint(0, 1000) == 0:
            print("I: Simulating a crash")
            break
        elif cycles > 1000 and randint(0, 100) == 0:
            print("I: Simulating CPU overload")
            time.sleep(2)


    serverZMQ.close()
    context.term()


def send_rep(result,request_clear):
    send_hash = node.thishash(request_clear).encode()
    send_rep = {
        'send_hash': send_hash,
        'msg': result
    }
    # print(result_print)
    serverZMQ.send(str(send_rep).encode())

poh_active = server.load_poh_active()
test_poh_active(poh_active)  # при включении сервера/ноды пробуем провести транзакцию

my_thread = threading.Thread(target=get_msg, args=())
my_thread.start()

