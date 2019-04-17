import time
import zmq
import sys
import threading
from random import randint, random


import fu_tools

#  GLOBAL
VECTOR_FILE = 'node_vector.atm'
PATH_CFG = 'config/'
IP_NODE_FILE = 'ip_node.txt'
NODE_INFO_FILE = 'nodeinfo.atm'

#  Paranoid Pirate Protocol constants
PPP_END = b'\x01'  # Signals is END
REQUEST_TIMEOUT = 2000  # timeout


class AliveClientTask():
    """ClientTask"""
    def __init__(self,node):
        self.node = node

    def run(self):

        nodeinfo = fu_tools.nodeinfo()
        n = nodeinfo['node']
        vectorinfo = fu_tools.vectorinfo(n)

        dlina = vectorinfo['nodevectorlen']


        if dlina <= 1:
            ip_node = fu_tools.read_clear_text_file_split(PATH_CFG, IP_NODE_FILE)
            print('вы в сети один, запрашиваем вектор файл и пытаемся обработать нонсе')  # забираем сайдноду с файла ip_node
            self.nonce(ip_node[0])


        if dlina > 1:
            for key in range(1, dlina + 1):
                print(key)
                if key == n or vectorinfo['allvector'][key]['active'] == False:
                    print(key, ' - Нода выключена или является текущей')
                    continue
                print(vectorinfo['allvector'])
                print('Соединяюсь с node и ipport === ' + str(key) + ' ==== ', vectorinfo['allvector'][key]['ip'])
                #self.alive(ip_node)
                break

    #
    # поток связанный с сообщением о том, что я живой alive
    #

    def zmqstart(self,tcp):
        context = zmq.Context()
        socket = context.socket(zmq.DEALER)
        identity = "%04X-%04X" % (randint(0, 0x10000), randint(0, 0x10000))
        socket.identity = identity.encode('ascii')
        print('tcp://'+tcp+':5556')
        socket.connect('tcp://'+tcp+':5556')
        print('Клиент ',identity,' запустился')
        poll = zmq.Poller()
        poll.register(socket, zmq.POLLIN)
        return context,socket, poll


    #
    # поток связанный с сообщением о том, что я живой alive
    #
    def alive(self,tcp):
        context, socket, poll = self.zmqstart(tcp)
        send_msg = {'task': 'alive', 'msg': 'alive'}
        send_msg = str(send_msg).encode()
        socket.send(send_msg)
        print('Запрос Alive отправлен..')
        sockets = dict(poll.poll(REQUEST_TIMEOUT))

        if socket in sockets:
            msg = socket.recv()
            print(' Клиент %s ответил: %s' % (identity, msg))
        else:
            print('Мертвый ip или порт - остановка работы потока (попробуйте подключится снова или запросить данные по новым соседям)')
            #нет коннекта с нодой, выключаем ее в своем векторе
            nodeinfo = functools.nodeinfo()
            n = nodeinfo['node']
            vectorinfo = functools.vectorinfo(n)
            vectorinfo[n][nodechange]['active'] = False
            functools.write_dict_file(vectorinfo, PATH_CFG,VECTOR_FILE)
            print('выключили сайдноду - ', nodechange)
        socket.setsockopt(zmq.LINGER, 0)
        socket.close()
        context.term()

    #
    # поток связанный с запросом NONCE
    #
    def nonce(self,tcp):
        context, socket, poll = self.zmqstart(tcp)
        send_msg = {'task': 'nonce', 'msg': ''}
        send_msg = str(send_msg).encode()
        socket.send(send_msg)
        print('Сообщение nonce ушло')
        while True:
            sockets = dict(poll.poll(REQUEST_TIMEOUT))
            if socket in sockets:
                msg = socket.recv()
                # Validate control message, or return reply to client
                if PPP_END == msg:
                    print('Worker end')
                    break
                else:
                    msg = eval(msg)
                    print('Клиент ответил: %s' % (msg))
                    if msg['task'] == 'vector-file':
                        msg['task'] = 'vector-pow'
                        msg['msg'] = self.node.vector_take_last_node_for_make_NONCE(msg['msg'])
                        msg = str(msg).encode()
                        socket.send(msg)
                        print('====================')
                        print('Сообщение vector-pow ушло')
                        continue
                    if msg['task'] == 'vector-pow-valid':
                        print('Bro you in ATOM')
                        print(msg['msg'])
                        fu_tools.write_dict_file(msg['msg'],PATH_CFG,VECTOR_FILE)
                    else:
                        if msg['task'] == 'vector-pow-denine':
                            print('Bro you hash is SHIT')
                        else:
                            print('Something wrong')
            else:
                print('Мертвый ip или нет ответа - остановка работы потока (попробуйте подключится снова или запросить данные по новым соседям)')
                break
        socket.setsockopt(zmq.LINGER, 0)
        socket.close()
        context.term()
        print('tyt')


#
# это порт чисто для обработки взаимодействия последних нод
# получаем сообщения от других нод и обрабатываем их
#
class ServerTask(threading.Thread):
    """ServerTask"""
    def __init__(self,node):
        threading.Thread.__init__ (self)
        self.node = node

    def run(self):
        context = zmq.Context()
        frontend = context.socket(zmq.ROUTER)
        frontend.bind('tcp://*:5556')

        backend = context.socket(zmq.DEALER)
        backend.bind('inproc://backend')

        workers = []
        for i in range(5):
            worker = ServerWorker(context)
            worker.start()
            workers.append(worker)

        zmq.proxy(frontend, backend)

        frontend.close()
        backend.close()
        context.term()


class ServerWorker(threading.Thread):
    """ServerWorker"""
    def __init__(self, context):
        threading.Thread.__init__ (self)
        self.context = context

    def run(self):
        worker = self.context.socket(zmq.DEALER)
        worker.connect('inproc://backend')
        identity_w = "%04X-%04X" % (randint(0, 0x10000), randint(0, 0x10000)) # это внутренний id, не zmq
        print('Worker '+identity_w+' started')
        while True:
            ident, msg = worker.recv_multipart()
            print('Worker received %s from %s' % (msg, ident))
            self.test_task(worker,ident,msg)
            #replies = randint(0,3)
            #for i in range(replies):
                #time.sleep((randint(0,2)))
                #msg = eval(msg)
                #msg['worker'] = identity_w
                #msg = str(msg).encode()
                #worker.send_multipart([ident, msg])
        worker.close()

    def test_task(self,worker,ident,msg):
        msg = eval(msg)
        # запрос last vector для поиска nonce
        if 'nonce' in msg['task']:
            print('Запрос vector')
            msg['task'] = 'vector-file'
            msg['msg'] = self.node.vector_only_my_node_GET()
            msg = str(msg).encode()
            worker.send_multipart([ident, msg])
            return

        if 'vector-pow' in msg['task']:
            print('Запрос vector pow')
            msg = self.node.vector_check_POW(msg['msg'])
            msg = str(msg).encode()
            worker.send_multipart([ident, msg])
            worker.send_multipart([ident, PPP_END])
            return

        if 'http-pay' in msg['task']:
            print('Запрос http-pay')
            self.node.mynode_mempool.append(msg['msg'])
            print('=================')
            print('MEMPOOL: ',self.node.mynode_mempool)
            msg['task'] = 'http-pay-answer'
            msg['msg'] = {'node':self.node.mynode_number,'ip':self.node.mynode_ip}
            msg = str(msg).encode()
            worker.send_multipart([ident, msg])
            return


#
# это порт чисто для обработки взаимодействия последних нод
# получаем сообщения от других нод и обрабатываем их
#
class ClientTask(threading.Thread):
    """ServerTask"""
    def __init__(self,node):
        threading.Thread.__init__ (self)
        self.node = node

    def run(self):
        context = zmq.Context()

        workers = []

        worker = ClientWorker(context)
        worker.start()
        workers.append(worker)

        context.term()


class ClientWorker(threading.Thread):
    """ServerWorker"""
    def __init__(self, context):
        threading.Thread.__init__ (self)
        self.context = context

    def run(self):
        print('make some Client work')
        if self.node.mynode_blockchain_work == False: #проверка блокировщика работы с одним файлом блокчейна
            secure_random = random.SystemRandom()
            self.knock_knock_bro(secure_random.choice(self.node.mynode_vector_activelist))

    def knock_knock_bro(self,node_number):















