import redis
import pickle
import hashlib
import binascii
import zmq
import os
import time

import fu_tools

from decimal import Decimal,getcontext

import threading
from random import randint, random

import socket
import time


#  GLOBAL
VECTOR_FILE = 'node_vector.atm'
PATH_SYS = 'chain/config/'
PATH_CFG = 'config/'
IP_NODE_FILE = 'ip_node.txt'
NODE_INFO_FILE = 'nodeinfo.atm'

REQUEST_TIMEOUT = 3000  # timeout

getcontext().prec = 7

class Node:
    """ClientTask"""
    def __init__(self):
        self.mynode_number = self.nodeinfo('my')
        self.mynode_adr = self.nodeinfo('adr')
        self.mynode_ip = self.nodeinfo('ip')
        self.mynode_mempool = []
        self.mynode_vector = self.vectorinfo()
        self.mynode_blockchain_work = False
        self.mynode_vector_activelist = self.vectoractivelist()

    def load_and_send(self, msg):
        r = redis.StrictRedis(host='localhost', db=0)

        #открываем файл ноды для получниея комиссии и записи транзакции
        atom_system_file = self.nodeinfo()
        pbkey_node_adress = atom_system_file['send_adr']


        pay_atom_use = self.pay_redis(msg['from'], msg['count'], msg['send'],r)  # pay atom
        pay_comission_atom_use = self.pay_redis(msg['from'], msg['send_komis'], pbkey_node_adress, r)  # pay comission

        result = self.pay_blockchain(pay_atom_use, msg['from'], msg['count'], msg['send'], 'pay', msg['send_komis'])  # pay atom
        result = self.pay_blockchain(pay_atom_use,msg['from'], msg['send_komis'], pbkey_node_adress,'comis',0) # pay comission

        result_mainchain = self.mainchain('chain/mainchain/',msg['from'],msg['send'],msg['count'],msg['send_komis'],pbkey_node_adress) # make main blockchain


        self.write_dict_file(atom_system_file,'chain/config/','nodeinfo.atm')

        try:
            r.bgsave()
        except redis.exceptions.ResponseError:
            print('REDIS err: Background save already in progress')

        response = {
            'block':result_mainchain,
            'use atom':pay_atom_use
        }

        return response


    def mainchain(self, path,adr_from,adr_send,count,send_komis,pbkey_node_adress):
        count_files = next(os.walk(path))[2]  # dir is your directory path as string
        count_files = len(count_files)
        filename_this = str(count_files) + '.atm'
        filename_main_prev = str(count_files-2) + '.atm'

        prev_hash = self.thishash(self.read_dict_file(path, filename_main_prev))
        atom_main_data = {
            'timestamp': time.time(),
            'from': adr_from,
            'to': adr_send,
            'discription': '',
            'prev_hash': prev_hash
        }
        atom_main_data['discription'] = {
            'tx count': count,
            'comission': send_komis
        }
        self.write_dict_file(atom_main_data, path, filename_this)  # пишем main файл
        return count_files



    def pay_blockchain(self, pay_atom_use,adr_from, count_clear, adr_send,event,send_komis):
        count = Decimal(count_clear)
        if len(adr_send) < 28 or len(adr_send) > 10 and len(pay_atom_use)>0 and count != 0:  # критическая ошибка, если pay atom use будет пустой, тогда будет искючение

            for i in pay_atom_use['atom_use']:

                if self.test_atom_main_core(i) == True:  # проверка на целостность атома, проходим всю цепочку транзакций

                    k = 0
                    path = 'chain/' + str(i) + '/'
                    count_files = next(os.walk(path))[2]  # dir is your directory path as string
                    count_files = len(count_files)
                    filename_main = '!' + str(i) + '_main.atm'
                    atom_main_core_file = self.read_dict_file(path, filename_main)

                    if adr_from in atom_main_core_file[i]:
                        index_atom_count = Decimal(atom_main_core_file[i][adr_from])
                        if index_atom_count <= count:  # если в протоне хватает бабла
                            atom_main_core_file[i][adr_send] = atom_main_core_file[i].pop(adr_from)  # предыдущий владелец перезаписывается нынешним
                            count = count - index_atom_count
                            self.write_dict_file(atom_main_core_file, path, filename_main)  # пишем main файл
                            self.make_next_atom_in_blockchain(count_files,i,adr_from,adr_send,count_clear,index_atom_count,send_komis,event)
                            # пишем данные в атомчейн
                        else:
                            ostatok = index_atom_count - count
                            if adr_send == adr_from:
                                ostatok = ostatok + count
                                atom_main_core_file[i][adr_send] = str(ostatok)
                            else:
                                atom_main_core_file[i][adr_from] = str(ostatok)
                                atom_main_core_file[i][adr_send] = str(count)
                            count = 0
                            self.write_dict_file(atom_main_core_file, path, filename_main)  # пишем main файл
                            self.make_next_atom_in_blockchain(count_files,i,adr_from,adr_send,count_clear,count,send_komis,event)
                            # self.package_atom_in_file(pay_atom_use[i],pbkey_send,atom_main_core_file)
                        if count == 0:
                            break
                if count == 0:
                    break

    def make_next_atom_in_blockchain(self, count_files,i,adr_from,adr_send,count_clear,count_in_atom,send_komis,event):
        path = 'chain/' + str(i) + '/'
        filename_new_atom_blockchain = str(i) + '_' + str(count_files-1) + '.atm'

        if count_files == 2: # если есть только генезис транзакция, тогда
            filename_genesis = str(i) + '_0.atm'
            prev_hash = self.thishash(self.read_dict_file(path, filename_genesis))
            atom_file_data = {
                'num' : count_files-1,
                'from': adr_from,
                'to': adr_send,
                'count in atom': str(count_in_atom),
                'discription': '',
                'prev_hash': prev_hash
            }
            atom_file_data['discription'] = {
                'event': event,
                'tx count' : count_clear,
                'comission': send_komis
            }
            self.write_dict_file(atom_file_data,path,filename_new_atom_blockchain)  # записываем новую транзакцию в блокчейн конкретного атома

        if count_files > 2: # есть запись помимо генезиса
            filename_prev = str(i) + '_' + str(count_files-2) + '.atm'
            prev_hash = self.thishash(self.read_dict_file(path,filename_prev))
            atom_file_data = {
                 'num' : count_files - 1,
                 'from': adr_from,
                 'to' : adr_send,
                 'count in atom': str(count_in_atom),
                 'discription': '',
                 'prev_hash': prev_hash
            }
            atom_file_data['discription'] = {
                'event': event,
                'tx count' : count_clear,
                'comission': send_komis
            }
            self.write_dict_file(atom_file_data, path,filename_new_atom_blockchain)  # записываем новую транзакцию в блокчейн конкретного атома

    def test_atom_main_core(self,pay_atom_use):
        path = 'chain/' + str(pay_atom_use) + '/'
        atom = {}
        k = 0
        count_files = next(os.walk(path))[2]  # dir is your directory path as string
        count_files = len(count_files) - 1  # -1 because odd main file
        response = True
        while True:
            count_files -= 1
            filename = str(pay_atom_use) + '_' + str(count_files) + '.atm'
            if os.access(path + filename, os.F_OK) == True:
                atom[count_files] = self.read_dict_file(path, filename)

                if count_files == 0:  # если монета генезис
                    response = True
                    break

                if count_files > 0 and k > 0:  # если цепочка не генесис, а уже были транзакции, тогда проверяем хеши
                    if atom[count_files+1]['prev_hash'] == self.thishash(atom[count_files]):  # проверка на хеши в цепочке
                        response = True
                    else:
                        response = False
                        break
                    # - тут проверку на  подпись в цепочке
                    # - и тут проверку на целостьность монеты при последних транзакциях до целого значения атома
                k = 1
            else:
                break
        return response


    def read_dict_file(self,path,filename):
        with open(path+filename, 'rb') as f:
            dict = pickle.load(f)
        return dict

    def write_dict_file(self, dict,path,filename):
        if not os.path.exists(path):
            os.makedirs(path)
        with open(path+filename, 'wb') as f:
             pickle.dump(dict, f)

    def read_clear_text_file_split(self,path,filename):
        dict = open(path+filename).read().splitlines()
        return dict

    def write_clear_text_in_file(self, dict,path,filename):
        if not os.path.exists(path):
            os.makedirs(path)
        with open(path+filename, 'w') as f:
            f.write(dict)
        print('записан')


    def add_dict_file(self, dict,path,filename):
        if not os.path.exists(path):
            os.makedirs(path)
        with open(path+filename, 'ab') as f:
             pickle.dump(dict, f)

    def write_atom_file(self, dict, number_of_chain):
        with open('chain/' + str(number_of_chain) + '.atm', 'wb') as f:
            pickle.dump(dict, f)

    def nodeinfo(self,task):
        node = self.read_dict_file(PATH_CFG, NODE_INFO_FILE)
        if task == 'my':
            return node['node']
        if task == 'adr':
            return node['send_adr']
        if task == 'ip':
            return node['ip']
        return node

    def vectorinfo(self):
        dict = self.read_dict_file(PATH_CFG,VECTOR_FILE)
        return dict

    # список активных нод кроме моей
    def vectoractivelist(self):
        vectorlist = []
        for key in self.mynode_vector:
            if self.mynode_number != key and self.mynode_vector[key]['active'] == True:
                vectorlist.append(self.mynode_vector[key]['node'])
        return vectorlist

    def prevhash(self, now_atom):
        now_atom = now_atom-1  #номер нужного файла для хеша
        with open('chain/' + str(now_atom) + '.atm', 'rb') as f:
            dict = pickle.load(f)
        hash_prev = hashlib.sha256(str(dict).encode()).digest()
        hash_prev = binascii.hexlify(hash_prev).decode('ascii')
        return hash_prev

    def thishash(self, dict):
        hash = hashlib.sha256(str(dict).encode()).digest()
        hash = binascii.hexlify(hash).decode('ascii')
        return hash


    def package_atom_in_data(self, atom_use,pbkey_send,r):
        #r = redis.StrictRedis(host='localhost', db=0)
        send = {}
        node = {}
        #
        # Прогоняем в цикле список атомов в которых надо проверить и суммировать данные
        #
        for i in range(len(atom_use)):
            data = r.lrange(atom_use[i], 0, -1)
            proton_del = []
            money_count = 0
            #
            # Определяем разброс монет в атоме и создаем данные для суммирования
            # list начинается с 0!,  list redis начинается с 1!
            #
            for j in range(len(data)):  # цикл внутри выбранного атома в list
                if pbkey_send == data[j].decode():
                    if money_count>0:
                        proton_del.append(j + 1)  # какие протоны под удаление
                    else:
                        proton = j + 1  # протон куда сумируем надйенные деньги
                    money_count = money_count + Decimal(data[j + 1].decode())  # складываем монетки найденные в атоме, для объединения
            #
            # Пишем данные в redis в конкретный атом и удаляем лищнее
            #
            if len(proton_del) != 0:
                r.lset(atom_use[i], proton, money_count)
                #
                # ебаный костыль для удаления из redis, я хз как это говно норм удалить
                #
                k = 0
                for g in range(len(proton_del)):
                    r.lset(atom_use[i],proton_del[g],pbkey_send)
                    k += 1
                data = r.lrange(atom_use[i], 0, -1)
                r.lrem(atom_use[i], k*-1*2, pbkey_send)  # удаляем все протоны из атома по адресу c конца


# удалить!
    def send_to_all_node(self, rnd_node,data):
        context = zmq.Context(1)
        client = context.socket(zmq.REQ)
        SERVER_ENDPOINT = "tcp://192.168.0.100:5555"
        client.connect(SERVER_ENDPOINT)
        poll = zmq.Poller()
        poll.register(client, zmq.POLLIN)
        REQUEST_TIMEOUT = 2500
        REQUEST_RETRIES = 3
        retries_left = REQUEST_RETRIES

        while retries_left:
            data_send = {'wtf': '1','rnd': rnd_node, 'msg_no_sig': data}
            data_send = str(data_send).encode()
            request = data_send
            print("Пересылаю данные (%s)" % request)
            client.send(request)

            expect_reply = True
            while expect_reply:
                socks = dict(poll.poll(REQUEST_TIMEOUT))
                if socks.get(client) == zmq.POLLIN:
                    reply = client.recv()
                    if not reply:
                        break
                    if reply.decode() == self.thishash(request):
                        print("I: Server replied OK (%s)" % reply)
                        retries_left = 0
                        expect_reply = False
                    else:
                        print("E: Malformed reply from server: %s" % reply)

                else:
                    print("W: No response from server, retrying…")
                    # Socket is confused. Close and remove it.
                    client.setsockopt(zmq.LINGER, 0)
                    client.close()
                    poll.unregister(client)
                    retries_left -= 1
                    if retries_left == 0:
                        print("E: Server seems to be offline, abandoning")
                        break
                    print("I: Reconnecting and resending (%s)" % request)
                    # Create new connection
                    client = context.socket(zmq.REQ)
                    client.connect(SERVER_ENDPOINT)
                    poll.register(client, zmq.POLLIN)
                    client.send(request)
        return str(data)

    def check_node_number(self,nodeinfo,nodevector):
        if len(nodevector)<2:
            return 'You robinson cruso'
        context = zmq.Context(1)
        client = context.socket(zmq.REQ)
        SERVER_ENDPOINT = "tcp://213.158.1.6:5555"
        client.connect(SERVER_ENDPOINT)
        poll = zmq.Poller()
        poll.register(client, zmq.POLLIN)
        REQUEST_TIMEOUT = 1000
        REQUEST_RETRIES = 1
        retries_left = REQUEST_RETRIES

        while retries_left:
            data_send = {'wtf': '1','rnd': rnd_node, 'msg_no_sig': data}
            data_send = str(data_send).encode()
            request = data_send
            print("I: Пересылаю (%s)" % request)
            client.send(request)

            expect_reply = True
            while expect_reply:
                socks = dict(poll.poll(REQUEST_TIMEOUT))
                if socks.get(client) == zmq.POLLIN:
                    reply = client.recv()
                    if not reply:
                        break
                    if reply.decode() == self.thishash(request):
                        print("I: Server replied OK (%s)" % reply)
                        retries_left = 0
                        expect_reply = False
                    else:
                        print("E: Malformed reply from server: %s" % reply)

                else:
                    print("W: No response from server, retrying…")
                    # Socket is confused. Close and remove it.
                    client.setsockopt(zmq.LINGER, 0)
                    client.close()
                    poll.unregister(client)
                    retries_left -= 1
                    if retries_left == 0:
                        print("E: Server seems to be offline, abandoning")
                        break
                    print("I: Reconnecting and resending (%s)" % request)
                    # Create new connection
                    client = context.socket(zmq.REQ)
                    client.connect(SERVER_ENDPOINT)
                    poll.register(client, zmq.POLLIN)
                    client.send(request)
        return str(data)


    def pay_redis(self, adr_from, count, adr_send,r):
        atom_use = []
        count = Decimal(count)
        if len(adr_send) < 28 or len(adr_send) > 10:
            for i in range(0, r.dbsize()):
                for j in range(0, r.llen(i)):
                    if r.lindex(i, j).decode() == adr_from:  # если сумма выплаты еще не достигал количества платежа
                        index_atom_count = Decimal(r.lindex(i, j + 1).decode())
                        if index_atom_count <= count:  # если в протоне хватает бабла
                            r.lset(i, j, adr_send)  # пишем в локальную ноду новые данные
                            count = count - index_atom_count
                            atom_use.append(i)
                            # пишем данные в атомчейн
                        else:
                            ostatok = index_atom_count - count
                            r.lset(i, j + 1, ostatok.normalize())
                            r.rpush(i, adr_send)
                            r.rpush(i, count)
                            atom_use.append(i)
                            count = 0
                        if count == 0:
                            break
                if count == 0:
                    break
            self.package_atom_in_data(atom_use, adr_send, r)  # пакуем атомы
            response = {
                'atom_use': atom_use
                }
            return response


        #
        # POH consensus between node
        #
    def poh(self,dict,node_count):
        alf = "abcdefghijklmnopqrstuvwxyz"
        hash = self.thishash(dict)
        hash = hash.lower()
        hash_modif = hash
        # hash_modif_sum = 1
        for i in range(len(hash)):
            if hash[i] in alf:
                hash_modif = hash_modif.replace(hash[i], str(ord(hash[i])))
        hash_sum = node_count + 10
        round = 0
        while hash_sum > node_count and hash_sum > 9:
            round += 1
            hash_modif = hash_modif.replace(str(round - 1), str(round))
            hash_modif_sum = hash_modif
            while hash_sum > node_count and hash_sum > 9:
                hash_sum = int(hash_modif_sum[:1]) + int(hash_modif_sum[1:len(hash_modif)])
                hash_modif_sum = str(hash_sum)

            break

        # если нод меньше 9, тогда
        if node_count < 9:
            hash_modif_sum = int(hash_modif_sum)
            while hash_modif_sum > node_count:
                hash_modif_sum = hash_modif_sum // 2
        return int(hash_modif_sum)

    #
    # POH consensus tx
    #
    def poh_tx(self, dict):
        node_count = len(self.mynode_vector)
        alf = "abcdefghijklmnopqrstuvwxyz"
        hash = self.thishash(dict)
        hash = hash.lower()
        hash_modif = hash
        for i in range(len(hash)):
            if hash[i] in alf:
                hash_modif = hash_modif.replace(hash[i], str(ord(hash[i])-96))
        hash_sum = node_count + 10
        round = 0
        while hash_sum > node_count and hash_sum > 9:
            round += 1
            hash_modif = hash_modif.replace(str(round - 1), str(round))
            hash_modif_sum = hash_modif
            while hash_sum > node_count and hash_sum > 9:
                hash_sum = int(hash_modif_sum[:1]) + int(hash_modif_sum[1:len(hash_modif)])
                hash_modif_sum = str(hash_sum)

            break

        # если нод меньше 9, тогда
        if node_count < 9:
            hash_modif_sum = int(hash_modif_sum)
            while hash_modif_sum > node_count:
                hash_modif_sum = hash_modif_sum // 2
        return int(hash_modif_sum)


    #
    # ADD NEW NODE IN VECTOR
    #
    def add_new_node(self,block):
        node_config = self.nodeinfo()
        n = node_config['node']
        directory = 'chain/config/'
        filename = 'node_vector.atm'
        node_vector = self.read_dict_file(directory,filename)

        for key, value in node_vector.items():
            for key2, value2 in node_vector[key].items():
                if block['adress'] in node_vector[key][key2].values():
                    return 'This adr has in vect file, not add'

        dlina = len(node_vector[n])
        if block['next_key'] == node_vector[n][dlina]['next_key']:
            hash = self.thishash(block)
            if hash[0] == '0':
                node_vector[n][dlina] = block
                node_vector[n][dlina+1] = {
                    'node': 'wait',
                    'adress': 'wait',
                    'ipport': 'wait',
                    'active': False,
                    'next_key': self.poh(block,1000000),
                    'nonce': 0
                }
                node_vector[dlina] = node_vector[n]
                self.write_dict_file(node_vector,'chain/config/','node_vector.atm')
                result = {
                        'vector' : '1',
                        'data' : node_vector,
                        'result' : 'Add in global vector file'
                    }
                return result
            else:
                return 'Result: POW hash wrong'
        else:
            return 'Result: Not equal next_key'


    def try_connect_to_network(self,dict_send,base_node):
        context = zmq.Context(1)
        client = context.socket(zmq.REQ)
        identity = "%04X-%04X" % (randint(0, 0x10000), randint(0, 0x10000))
        client.setsockopt(zmq.IDENTITY, identity)
        SERVER_ENDPOINT = 'tcp://'+base_node+':5556'
        client.connect(SERVER_ENDPOINT)
        poll = zmq.Poller()
        poll.register(client, zmq.POLLIN)
        REQUEST_TIMEOUT = 3000
        REQUEST_RETRIES = 2
        retries_left = REQUEST_RETRIES

        while retries_left:
            data_send = dict_send
            data_send = str(data_send).encode()
            request = data_send
            print("Пересылаю ", base_node, ':', request)
            client.send(request)
            data = ''
            expect_reply = True
            while expect_reply:
                socks = dict(poll.poll(REQUEST_TIMEOUT))
                if socks.get(client) == zmq.POLLIN:
                    reply = client.recv()
                    reply = eval(reply.decode())
                    if not reply:
                        data = 'break, not reply recive'
                        break
                    if reply['task'].decode() == 'http-pay-answer':
                        print("Ответ сервера: (%s)" % reply)
                        retries_left = 0
                        data = str(reply['msg'])
                        expect_reply = False
                    else:
                        print("E: Malformed reply from server: %s" % reply)

                else:
                    data = 'no response'
                    print("W: No response from server, retrying…")
                    # Socket is confused. Close and remove it.
                    client.setsockopt(zmq.LINGER, 0)
                    client.close()
                    poll.unregister(client)
                    retries_left -= 1
                    if retries_left == 0:
                        print("E: Server seems to be offline, abandoning")
                        break
                    print("I: Reconnecting and resending (%s)" % request)
                    # Create new connection
                    client = context.socket(zmq.REQ)
                    client.connect(SERVER_ENDPOINT)
                    poll.register(client, zmq.POLLIN)
                    client.send(request)
        return data

    def try_connect_to_router(self,dict_send,base_node):
        SERVER_ENDPOINT = 'tcp://' + base_node + ':5556'
        context = zmq.Context()
        socket = context.socket(zmq.DEALER)
        identity = "%04X-%04X" % (randint(0, 0x10000), randint(0, 0x10000))
        socket.identity = identity.encode('ascii')
        socket.connect(SERVER_ENDPOINT)
        poll = zmq.Poller()
        poll.register(socket, zmq.POLLIN)


        send_msg = str(dict_send).encode()
        socket.send(send_msg)
        print('Запрос http-pay отправлен..')
        sockets = dict(poll.poll(REQUEST_TIMEOUT))

        if socket in sockets:
            msg = socket.recv()
            msg = eval(msg)
            if msg['task'] == 'http-pay-answer':
                print("Ответ сервера: (%s)" % msg)
            else:
                print(' Клиент %s ответил: %s' % (identity, msg))

        else:
            print('Мертвый ip?')
        socket.close()
        context.term()




    def make_nonce_VECTOR(self,zapros_adr, ipport,base_node):
        directory = 'chain/config/'
        filename = 'node_vector.atm'
        node_vector = self.read_dict_file(directory,filename)
        for key, value in node_vector.items():
            for key2, value2 in node_vector[key].items():
                if 'next_key' in node_vector[key][key2].keys() and node_vector[key][key2]['node']=='wait':
                    vector_pow = {
                        'node': len(node_vector[key]),
                        'adress': zapros_adr,
                        'ipport': ipport,
                        'active': False,
                        'next_key': node_vector[key][key2]['next_key'],
                        'nonce':0
                    }
                    while True:
                        hash = self.thishash(vector_pow)
                        if hash[0] == '0':

                            result = {'addmeplz': '1', 'msg': vector_pow}  # просимся добавить нас в ветор файл нод
                            result = self.try_connect_to_network(result, base_node)

                            if 'vector' in result:
                                result = eval(result)
                                if result['vector'] == '1':
                                    #node_vector[key][key2] = vector_pow
                                    #self.write_dict_file(node_vector, directory, filename)

                                    nodeinfo = self.nodeinfo()
                                    nodeinfo['node'] = len(result['data'])
                                    self.write_dict_file(nodeinfo, directory, filename)

                                    directory = 'chain/config/'
                                    filename = 'node_vector.atm'
                                    self.write_dict_file(result['data'], directory, filename)


                                    return 'get vector and rewrite file'
                            else:
                                return result
                        else:
                            vector_pow['nonce'] = vector_pow['nonce']+1
        return 'err:make_nonce_VECTOR - false'


    # проверка приходящего вектора хешей от другой ноды. если каких-то хешей нет, тогда задача добавляется в список запросов от других нод
    def check_mempool_hash(self,tx):
        path = 'chain/config/'
        filename = 'txpool_swamp.atm'
        self.add_dict_file(tx, path, filename)
        return 'thx, add to mempool tx hash'

    #
    # проверка присланной транзакции от другой ноды, тоесть проверка что она имело права проводить транзакцию, и
    # что ее транзакция верная и поступилиа именно к ней в ноду и плюс получить все последние транзакции, коих я не имею.
    #
    def check_tx_from_another_node(self, msg):
        print('cl_node 680:', msg)
        nodeinfo = self.nodeinfo()
        rnd_node_count = self.rnd_node_count(nodeinfo['node'])
        result = 0
        filename = 'node_vector.atm'
        node_vector = self.read_dict_file(path, filename)

        for i in range(1,len(node_vector[nodeinfo['node']])):
            if msg['descr']['node_from'] == node_vector[nodeinfo['node']][i]['node']:
                result = i
                break
        msg.pop('descr')
        if result == self.poh_tx(msg, rnd_node_count):
            if nodeinfo['node'] == self.poh(msg,rnd_node_count):
                return True
        return False


    # количество нод в данной ноде
    def rnd_node_count(self,node_id):
        path = 'chain/config/'
        filename = 'node_vector.atm'
        result = self.read_dict_file(path, filename)
        node_count = len(result[node_id])
        if result[node_id][node_count]['node'] == 'wait':
            node_count -= 1
        return node_count

        # количество нод в данной ноде
    def lastblock(self,path):
        count_files = next(os.walk(path))[2]  # dir is your directory path as string
        count_files = len(count_files)
        return count_files


    # проверка lake файла на наличие транзакций
    def get_hash_all_tx(self):
        k = 1
        vector_hash = {}
        path = 'chain/config/'
        filename = 'txpool_leak.atm'

        with open(path + filename, 'rb') as f:
            while True:
                try:
                    vector_hash[k] = self.thishash(pickle.load(f))
                    k += 1
                except EOFError:
                    break
        return vector_hash


    # получаем внутренний/локальный ip
    def get_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    # получаем блоки с пред ноды
    def getblockfromprevnode(self,dict):
        lastblock = node.lastblock('chain/mainchain/')
        if dict['descr']['block'] > lastblock:
            print('cl_node, 761, blocke MORE: ', lastblock, ' = ', dict['descr']['block'])
            result = {'givemeplzlastblock': '1', 'msg': lastblock}  # просимся добавить нас в ветор файл нод
            result = self.try_connect_to_network(result, base_node)
        else:
            print('cl_node, 763, blocke NOT MORE: ', lastblock, ' = ', dict['descr']['block'])
        result = node.check_tx_from_another_node(dict)
        return result


    def alive(self,alive_node):
        node_config = self.nodeinfo()
        n = node_config['node']
        filename = 'node_vector.atm'
        node_vector = self.read_dict_file(path,filename)
        node_vector[n][alive_node]['active'] = True
        node_vector[n][n]['active'] = True
        node_vector[alive_node][alive_node]['active'] = True
        print('alive cl_node 766:', node_vector[n][alive_node]['active'])
        print('alive cl_node 766:', node_vector[alive_node][alive_node]['active'])
        print('alive_node:', alive_node,'; ', 'n: ', n)
        print(node_vector)
        self.write_dict_file(node_vector,path,filename)
        return 'live bro'

    # если в файле ноды есть активация проведения транзакции, то нода ее старается провести???
    def alive_start_client(self):
        dict = {'iamalive': 0, 'msg': ''}
        nodeinfo = self.nodeinfo()
        n = nodeinfo['node']
        vectorinfo = self.vectorinfo(n)

        dlina = vectorinfo['nodevectorlen']

        # если ноды две и больше, пытаемся связаться и сообщить, что вы в строю.
        if dlina <= 1:
            ip_node = self.read_clear_text_file_split(PATH_CFG,IP_NODE_FILE)
            alive = AliveClientTask('nonce', ip_node[0], '')
            alive.start()
            print('вы в сети один, запрашиваем вектор файл и пытаемся обработать нонсе') # забираем сайдноду с файла ip_node


        if dlina > 1:
            for key in range(1,dlina+1):
                if key == n or vectorinfo['allvector'][n][key]['active'] == False:
                    print(key,' - Нода выключена или является текущей')
                    continue
                print('Соединяюсь с node и ipport === '+ str(key) +' ==== ',vectorinfo['allvector'][n][key]['ipport'])
                alive = AliveClientTask('alive', vectorinfo['allvector'][n][key]['ipport'], key)
                alive.start()
                break


    def vector_only_my_node_GET(self):
        node_vector = self.read_dict_file(PATH_CFG, VECTOR_FILE)
        return node_vector[self.mynode_number]

    def vector_take_last_node_for_make_NONCE(self,msg):
        my_vector_node_file_pow = {}
        my_vector_node_file_pow[1] = dict(msg)
        my_vector_node_file_pow[2] = {
            'node': msg['node'] + 1,
            'adr': self.mynode_adr,
            'ip': self.mynode_ip,
            'nonce': 0
        }
        try:
            del my_vector_node_file_pow[1]['active']
            #msg[len(msg)].pop('active')
        except KeyError as ex:
            print("No such key: '%s'" % ex.message)
        while True:
            hash = self.thishash(my_vector_node_file_pow)
            if hash[0] == '0' and hash[1] == '0':
                print(str(my_vector_node_file_pow[2]['nonce']) +' : '+hash)
                my_vector_node_file_pow[2]['active'] = 'wait'
                nodeinfo = self.nodeinfo('0')
                nodeinfo['node'] = my_vector_node_file_pow[2]['node']
                self.write_dict_file(nodeinfo, PATH_CFG, NODE_INFO_FILE)
                self.mynode_number = nodeinfo['node']
                msg.update(my_vector_node_file_pow[2])
                print('msg: ', msg)
                return my_vector_node_file_pow[2]
            else:
                my_vector_node_file_pow[2]['nonce'] = my_vector_node_file_pow[2]['nonce'] + 1


    def vector_check_POW(self,msg):
        my_vector_node_file_pow = {}
        msg_return = {}

        vectorinfo = fu_tools.vectorinfo(self.mynode_number)

        my_vector_node_file_pow[1] = dict(vectorinfo['allvector'][len(vectorinfo['allvector'])])
        my_vector_node_file_pow[2] = msg
        print( my_vector_node_file_pow)

        try:
            del my_vector_node_file_pow[1]['active']
            del my_vector_node_file_pow[2]['active']
        except KeyError as ex:
            print("No such key: '%s'" % ex.message)
        print(my_vector_node_file_pow)
        hash = self.thishash(my_vector_node_file_pow)

        if hash[0] == '0' and hash[1] == '0':
            msg['active'] = True
            vectorinfo['allvector'][vectorinfo['nodevectorlen']+1] = msg
            fu_tools.write_dict_file(vectorinfo['allvector'],PATH_CFG,VECTOR_FILE)
            msg_return['task'] = 'vector-pow-valid'
            msg_return['msg'] = vectorinfo['allvector']
            return msg_return
        else:
            msg_return['task'] = 'vector-pow-denine'
            msg_return['msg'] = ''
            return msg_return










