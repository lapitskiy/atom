import redis
import pickle
import hashlib
import binascii
import zmq
import os
import time
from decimal import Decimal,getcontext

import socket
import time
import threading

getcontext().prec = 7

class Node:

    def load_and_send(self, pbkey_from, count, pbkey_send, send_komis):
        r = redis.StrictRedis(host='localhost', db=0)

        response_pay = self.pay(pbkey_from, count, pbkey_send,r)

        #открываем файл ноды для получниея комиссии и записи транзакции
        atom_system_file = self.read_system_file()
        atom_system_file['count'] = int(atom_system_file['count']) + 1
        pbkey_node_adress = atom_system_file['send_adr']
        response_komis = self.pay(pbkey_from, send_komis, pbkey_node_adress, r)
        prev_transaction_hash = self.prevhash(atom_system_file['count'])

        atom_file_data = {
            'timestamp' : time.time(),
            'num' : atom_system_file['count'],
            'from': pbkey_from,
            'to': pbkey_send,
            'count pay': str(count),
            'comission': send_komis,
            'hash': prev_transaction_hash
        }
        this_transaction_hash = self.thishash(atom_file_data)
        # send_to_all = self.send_to_all_node(this_transaction_hash)


        self.write_atom_file(atom_file_data, atom_system_file['count'])
        self.write_dict_file(atom_system_file,'chain/config/','nodeinfo.atm')

        r.bgsave()
        response = Decimal(count) + Decimal(send_komis)
        return str(response)

    def read_system_file(self):
        with open('chain/config/nodeinfo.atm', 'rb') as f:
            dict = pickle.load(f)
        return dict

    def read_dict_file(self,path,filename):
        with open(path+filename, 'rb') as f:
            dict = pickle.load(f)
        return dict

    def write_dict_file(self, dict,path,filename):
        if not os.path.exists(path):
            os.makedirs(path)
        with open(path+filename, 'wb') as f:
             pickle.dump(dict, f)

    def write_atom_file(self, dict, number_of_chain):
        with open('chain/' + str(number_of_chain) + '.atm', 'wb') as f:
            pickle.dump(dict, f)

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

    @staticmethod
    def package_atom_in_data(atom_use,pbkey_send,r):
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
            print("I: Пересылаю (%s)" % request)
            client.send(request)

            expect_reply = True
            while expect_reply:
                socks = dict(poll.poll(REQUEST_TIMEOUT))
                if socks.get(client) == zmq.POLLIN:
                    reply = client.recv()
                    print(reply)
                    print(self.thishash(request))
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
            print('tyt')
            return 'You robinson cruso'
        context = zmq.Context(1)
        client = context.socket(zmq.REQ)
        SERVER_ENDPOINT = "tcp://213.158.1.6:5555"
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
            print("I: Пересылаю (%s)" % request)
            client.send(request)

            expect_reply = True
            while expect_reply:
                socks = dict(poll.poll(REQUEST_TIMEOUT))
                if socks.get(client) == zmq.POLLIN:
                    reply = client.recv()
                    print(reply)
                    print(self.thishash(request))
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


    def try_connect_to_network(self,dict_send,base_node):
        context = zmq.Context(1)
        client = context.socket(zmq.REQ)
        SERVER_ENDPOINT = 'tcp://'+base_node
        client.connect(SERVER_ENDPOINT)
        poll = zmq.Poller()
        poll.register(client, zmq.POLLIN)
        REQUEST_TIMEOUT = 2500
        REQUEST_RETRIES = 3
        retries_left = REQUEST_RETRIES

        while retries_left:
            data_send = dict_send
            data_send = str(data_send).encode()
            request = data_send
            print("I: Пересылаю (%s)" % request)
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
                    if reply['send_hash'].decode() == self.thishash(request):
                        print("Ответ сервера: (%s)" % reply)
                        retries_left = 0
                        data = 'answer: ' + str(reply['msg'])
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
        return str(data)

    def pay(self, pbkey_from, count, pbkey_send,r):
        atom_use = []
        count = Decimal(count)
        if len(pbkey_send) < 28 or len(pbkey_send) > 10:
            for i in range(0, r.dbsize()):
                for j in range(0, r.llen(i)):
                    if r.lindex(i, j).decode() == pbkey_from:  # если сумма выплаты еще не достигал количества платежа
                        index_atom_count = Decimal(r.lindex(i, j + 1).decode())
                        if index_atom_count <= count:  # если в протоне хватает бабла
                            r.lset(i, j, pbkey_send)  # пишем в локальную ноду новые данные
                            count = count - index_atom_count
                            atom_use.append(i)
                            # пишем данные в атомчейн
                        else:
                            ostatok = index_atom_count - count
                            r.lset(i, j + 1, ostatok.normalize())
                            r.rpush(i, pbkey_send)
                            r.rpush(i, count)
                            atom_use.append(i)
                            count = 0
                        if count == 0:
                            break
                if count == 0:
                    break
            self.package_atom_in_data(atom_use, pbkey_send, r)  # пакуем атомы
            response = {
                'atom_use': atom_use
                }
            return response

    def poh(self,dict,node_count):
        alf = "abcdefghijklmnopqrstuvwxyz"
        hash = self.thishash(dict)
        hash = hash.lower()
        node_len = len(str(node_count))
        hash_modif = hash
        for i in range(len(hash)):
            if hash[i] in alf:
                hash_modif = hash_modif.replace(hash[i], str(ord(hash[i])))
        hash_sum = node_count + 1
        round = 0
        stop = 0
        while hash_sum > node_count:
            round += 1
            hash_modif = hash_modif.replace(str(round - 1), str(round))
            hash_modif_sum = hash_modif
            tag = len(hash_modif)
            while tag > node_len:
                hash_sum = int(hash_modif_sum[:1]) + int(hash_modif_sum[1:len(hash_modif)])
                hash_modif_sum = str(hash_sum)
                tag = len(hash_modif_sum)
            stop += 1
        return hash_modif_sum

    def add_new_node(self,block):
        directory = 'chain/config/'
        filename = 'nodeinfo.atm'
        node_config = self.read_dict_file(directory, filename)
        n = node_config['node']
        directory = 'chain/config/'
        filename = 'node_vector.atm'
        node_vector = self.read_dict_file(directory,filename)
        for key, value in node_vector.items():
            if block['adress'] in node_vector[key].values():
                return 'This adr has in vector file, not add'
        dlina = len(node_vector[n])
        print(block['next_key'])
        print(node_vector[n][dlina]['next_key'])
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
        SERVER_ENDPOINT = 'tcp://'+base_node
        client.connect(SERVER_ENDPOINT)
        poll = zmq.Poller()
        poll.register(client, zmq.POLLIN)
        REQUEST_TIMEOUT = 2500
        REQUEST_RETRIES = 3
        retries_left = REQUEST_RETRIES

        while retries_left:
            data_send = dict_send
            data_send = str(data_send).encode()
            request = data_send
            print("I: Пересылаю (%s)" % request)
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
                    if reply['send_hash'].decode() == self.thishash(request):
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


    def make_nonce_VECTOR(self,zapros_adr, ipport):
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
                    print(vector_pow)
                    while True:
                        hash = self.thishash(vector_pow)
                        if hash[0] == '0':
                            node_vector[key][key2] = vector_pow
                            self.write_dict_file(node_vector,directory,filename)
                            return vector_pow
                        else:
                            vector_pow['nonce'] = vector_pow['nonce']+1
        print('I do not found next key')
        return 'make_nonce_VECTOR - false hash'

