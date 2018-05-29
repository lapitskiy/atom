from __future__ import print_function
from flask import Flask, jsonify, request, render_template, redirect, url_for, make_response
from cl_node import *
from random import randint
import os
from wallet import *

# zeroMQ

import zmq

#
#zeroMQ params fo lazy pirat
#



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
    dict = {
        'node': 1,
        'count': 0,
        'ip': 'tcp://*:5555',
        'send_adr': node_adr
    }
    directory = 'chain/config/'
    filename = 'nodeinfo.atm'
    node.write_dict_file(dict,directory,filename)
    return jsonify(result=dict)

@app.route('/genesis', methods=['GET', 'POST'])
def ajax_genesis():
    # make geniesis block
    atom_file_data = {}
    atom_vector_data = {}
    send_txt = request.args.get('send_txt', 0, type=str)
    node_adr = request.args.get('node_adr', 0, type=str)
    atom_file_data[1] = {
        'time capsule': send_txt,
        'atom': 0,
        'electron': 0,
        'adress': node_adr,
        'positron': 0,
        'count': 0
    }
    directory = 'chain/'
    if not os.path.exists(directory):
        os.makedirs(directory)
    with open(directory+'0.atm', 'wb') as f:
        pickle.dump(atom_file_data, f)
        # make genesis node vector number
    atom_vector_data[1] = {}
    atom_vector_data[1][1] = {
        'node': 1,
        'adress': node_adr,
        'ipport': '192.168.0.100:5555',
        'active': True,
        'next_key':0,
        'nonce':0
    }

    atom_vector_data[1][2] = {
        'node': 'wait',
        'adress': node_adr,
        'ipport': 'wait',
        'active': False,
        'next_key': randint(1, 1000000),
        'nonce': 0
    }

    print(str(atom_vector_data))
    directory = 'chain/config/'
    filename = 'node_vector.atm'
    node.write_dict_file(atom_vector_data,directory,filename)
    return jsonify(result=atom_file_data)

@app.route('/connect', methods=['GET', 'POST'])
def node_connect():
    msg = request.form
    msg_no_sign = {'send':msg['send'],'from':msg['from'],'count':msg['count'],'adr':msg['adr']}
    rnd_node = node.poh(msg_no_sign,10)
    verify = wallet.verify_sig(msg['from'],msg['sign'],msg_no_sign)
    if verify == True:
        msg_no_sign['sign'] = msg['sign']

        send_to_all = node.send_to_all_node(rnd_node,msg_no_sign)

        print(send_to_all)
        get_data = node.load_and_send(msg['adr'],msg['count'],msg['send'],msg['send_komis'])


        return jsonify(get_data), 200
    if verify == False:
        return jsonify('Bad sign'), 200
    return jsonify(verify), 200


@app.route('/zapros', methods=['GET', 'POST'])
def zapros():
    # make geniesis block
    return jsonify(result=result)

@app.route('/next_key', methods=['GET', 'POST'])
def next_key():
    # get next_key value
    base_node = request.args.get('base_node', 0, type=str)
    # result = node.get_last_vector_file_NET(base_node)

    result = {'getnextplz': '1', 'msg': 'Give me plz last vector next key'}  # просимся добавить нас в ветор файл нод
    result = node.try_connect_to_network(result, base_node)

    directory = 'chain/config/'
    filename = 'node_vector.atm'
    print(result)
    if result != 'false':
        node.write_dict_file(eval(result),directory,filename)
    return jsonify(result=result)

@app.route('/make_nonce', methods=['GET', 'POST'])
def make_nonce():
    zapros_adr = request.args.get('zapros_adr', 0, type=str)
    base_node = request.args.get('base_node', 0, type=str)
    ipport = request.args.get('ipport', 0, type=str)
    # make_nonce from next key
    result = node.make_nonce_VECTOR(zapros_adr, ipport)
    if result != 'false':
        result = {'addmeplz': '1', 'msg': result}  # просимся добавить нас в ветор файл нод
        result = node.try_connect_to_network(result, base_node)
        if 'vector' in result:
            result = eval(result)
            if result['vector'] == '1':
                directory = 'chain/config/'
                filename = 'nodeinfo.atm'
                nodeinfo = node.read_dict_file(directory, filename)
                nodeinfo['node'] = len(result['data'])
                print(nodeinfo)
                node.write_dict_file(nodeinfo, directory, filename)
                directory = 'chain/config/'
                filename = 'node_vector.atm'
                node.write_dict_file(result['data'], directory, filename)

    return jsonify(result=result)

if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5001, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='0.0.0.0', port=port)


