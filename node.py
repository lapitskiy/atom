from __future__ import print_function
from flask import Flask, jsonify, request, render_template, redirect, url_for, make_response
from cl_node import *
from random import randint
import os
import json
from wallet import *

# zeroMQ

import zmq

#
#zeroMQ params fo lazy pirat
#
#  GLOBAL
VECTOR_FILE = 'node_vector.atm'
PATH_SYS = 'chain/config/'
PATH_CFG = 'config/'
IP_NODE_FILE = 'ip_node.txt'
NODEINFO_FILE = 'nodeinfo.atm'

# Flask
# Instantiate the Node
app = Flask(__name__)
node = Node()  # Создаем объект Node
wallet = Wallet()  # Создаем объект Wallet

@app.route('/node', methods=['GET'])
def node_setting():
    return render_template('node.html')

@app.route('/ajax_get', methods=['GET', 'POST'])
def ajax_test():
    node_adr = request.args.get('send_adr', 0, type=str)
    node_pbkey = request.args.get('send_pbkey', 0, type=str)
    node_prkey = request.args.get('send_prkey', 0, type=str)
    dict = {
        'node': 1,
        'count': 0,
        'ip': node.get_ip(),
        'send_adr': node_adr,
        'send_pbkey': node_pbkey,
        'send_prkey': node_prkey
    }
    node.write_dict_file(dict,PATH_CFG,NODEINFO_FILE)
    return jsonify(result=dict)

@app.route('/genesis', methods=['GET', 'POST'])
def ajax_genesis():
    # make geniesis block
    atom_file_data = {}
    atom_vector_data = {}
    send_txt = request.args.get('send_txt', 0, type=str)
    node_adr = request.args.get('node_adr', 0, type=str)
    nonce_genesis = 0
    while True:
        atom_file_data[1] = {
            'time capsule': send_txt,
            'atom': 0,
            'electron': 0,
            'adress': node_adr,
            'positron': 0,
            'count': 0,
            'hash_prev' : nonce_genesis
        }
        poh_return = node.poh(atom_file_data,10)
        if poh_return == 1:
            print('poh return: ', poh_return,'; itter: ',nonce_genesis)
            break
        nonce_genesis += 1

    directory = 'chain/'
    if not os.path.exists(directory):
        os.makedirs(directory)
    with open(directory+'0.atm', 'wb') as f:
        pickle.dump(atom_file_data, f)

    #
    # make genesis node vector number
    #
    atom_vector_data = {}
    atom_vector_data[1] = {
        'node': 1,
        'adr': node_adr,
        'ip': node.get_ip(),
        'nonce':0,
        'active': True
    }


    node.write_dict_file(atom_vector_data,PATH_CFG,VECTOR_FILE)
    return jsonify(result=atom_file_data)

@app.route('/connect', methods=['GET', 'POST'])
def node_connect():
    msg = {}
    msg['msg'] = request.form.to_dict()
    directory = 'chain/config/'
    #filename = 'txpool_swamp.atm'
    msg['task'] = 'http-pay'
    #node.add_dict_file(msg,directory,filename)  # пишем в mempool
    pohnode = node.poh_tx(msg['msg'])
    print('pohnode ', pohnode)
    print('pohnode ip ', node.mynode_vector[pohnode]['ip'])
    if pohnode not in node.mynode_vector_activelist:
        result = 'poh node active=false, try again'
        return jsonify(result), 200
    #ip_node = fu_tools.read_clear_text_file_split(PATH_CFG, IP_NODE_FILE)
    node.try_connect_to_router(msg,node.mynode_vector[pohnode]['ip'])
    result = 'Add to mempool. wait verify you tx'
    """
    msg_no_sign = {'send':msg['send'],'from':msg['from'],'count':msg['count'],'adr':msg['adr']}
    rnd_node = node.poh(msg_no_sign,10)
    verify = wallet.verify_sig(msg['from'],msg['sign'],msg_no_sign)
    if verify == True:
        msg_no_sign['sign'] = msg['sign']
        send_to_all = node.send_to_all_node(rnd_node,msg_no_sign)
        get_data = node.load_and_send(msg['adr'],msg['count'],msg['send'],msg['send_komis'])


        return jsonify(get_data), 200
    if verify == False:
        return jsonify('Bad sign'), 200
    """
    return jsonify(result), 200


@app.route('/zapros', methods=['GET', 'POST'])
def zapros():
    # make geniesis block
    return jsonify(result=result)

#
# сервер включаем + включаем в node_vectro все active=true
#
@app.route('/test_activetrue', methods=['GET', 'POST'])
def test_activetrue():
    base_node = request.args.get('base_node', 0, type=str)
    path = 'chain/config/'
    filename = 'nodeinfo.atm'
    node_config = node.read_dict_file(path, filename)
    print(node_config)
    n = node_config['node']

    filename = 'node_vector.atm'
    node_vector = node.read_dict_file(path, filename)
    dlina = len(node_vector[n]) - 1
    for key in range(1, dlina + 1):
        node_vector[n][key]['active'] = True
    node.write_dict_file(node_vector,path,filename)
    # запускаем поток
    client = ClientTask('alive',base_node)
    client.start()
    result = 'Done'
    return jsonify(result=result)

@app.route('/genesistx', methods=['GET', 'POST'])
def genesistx():

    path = 'chain/config/'
    dict = {}
    k = 0

    nodeinfo = node.nodeinfo()
    vectorinfo = node.vectorinfo(nodeinfo['node'])

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
    if k > 0:
        print('tx in lake.atm, empty plz')
    if k == 0:  # озеро без рыбы, отправляем пустую транзакцию, для продолжения цепи
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
        msg['descr'] = result_load
        msg['descr']['node_from'] = nodeinfo['node']
        msg['descr']['vector_hash'] = vectorinfo['nodehashvector']

        filename = 'node_vector.atm'
        vector_file = node.read_dict_file(path, filename)
        ipport = vector_file[nodeinfo['node']][result2]['ipport']
        print(result2)
        print(vector_file[nodeinfo['node']][result2])
        result = {'yourtxnextbro': '1', 'msg': msg}  # сообщаем след. ноде, что ее задача
        print('-----------------------------')
        print('пытаемся связаться с ',ipport)
        print('-----------------------------')
        result = node.try_connect_to_network(result,ipport)
    else:
        print('Node not active in web')
    result = 'ok'
    """
    result = 'genesistx'
    base_node = request.args.get('base_node', 0, type=str)
    
    msg = {  # poh = 1; poh_tx = 2 # сообщение от ноды 2 к ноде 1
     'from': '4GBN73Uq97TaXBA1RgRJ8K2mB7Gj',
     'from_pbkey': '8ae0b9d3d44908334a44b23144edf9196773d9a5810e488bfd274f0c65a71da38bf7383feb5f09c4f7d414a0d245acb92044a53acfd59a8e45ce69a4ba4bcaf8',
     'count': '0.000004',
     'send': 'ZzzZzzVjE9tFhBJWYKLPFfKcqxSY',
     'send_komis': '0',
     'sign': 'cba28ef47ffae2bf333557ee91e746e37508ccd5244b121d7f72bd51cbc5ed6b158f9424a5b9ac8180733a269d4096fe79ac33f084df2ea91d838286d073f98c',
     'thishash': '424999d36d9fab957397a1a5fd5d123de3a3a0d015b02fe872e9acc78b1c8ea3'
         }

    result = {'yourtxnextbro': '1', 'msg': msg}  # просимся добавить нас в ветор файл нод
    print(base_node)
    result = node.try_connect_to_network(result, base_node)
    print('genesistx')
    """
    return jsonify(result=result)

@app.route('/next_key', methods=['GET', 'POST'])
def next_key():
    # get next_key value
    ip_node = request.args.get('ip_node', 0, type=str)
    print(ip_node)

    node.write_clear_text_in_file(ip_node,PATH_CFG,IP_NODE_FILE)

    return jsonify(result= ip_node)

@app.route('/make_nonce', methods=['GET', 'POST'])
def make_nonce():
    zapros_adr = request.args.get('zapros_adr', 0, type=str)
    base_node = request.args.get('base_node', 0, type=str)
    ipport = request.args.get('ipport', 0, type=str)
    # make_nonce from next key
    result = node.make_nonce_VECTOR(zapros_adr, ipport,base_node)
    return jsonify(result=result)

if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5001, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='0.0.0.0', port=port)


