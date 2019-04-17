import pickle
import hashlib
import binascii
import os

#  GLOBAL
VECTOR_FILE = 'node_vector.atm'
PATH_CFG = 'config/'
IP_NODE_FILE = 'ip_node.txt'
NODE_INFO_FILE = 'nodeinfo.atm'


def read_dict_file(path, filename):
    with open(path + filename, 'rb') as f:
        dict = pickle.load(f)
    return dict


def write_dict_file(dict, path, filename):
    if not os.path.exists(path):
        os.makedirs(path)
    with open(path + filename, 'wb') as f:
        pickle.dump(dict, f)


def read_clear_text_file_split(path, filename):
    dict = open(path + filename).read().splitlines()
    return dict


def write_clear_text_in_file(dict, path, filename):
    if not os.path.exists(path):
        os.makedirs(path)
    with open(path + filename, 'w') as f:
        f.write(dict)
    print('записан')


def add_dict_file(dict, path, filename):
    if not os.path.exists(path):
        os.makedirs(path)
    with open(path + filename, 'ab') as f:
        pickle.dump(dict, f)


def write_atom_file(dict, number_of_chain):
    with open('chain/' + str(number_of_chain) + '.atm', 'wb') as f:
        pickle.dump(dict, f)


def nodeinfo():
    node = read_dict_file(PATH_CFG, NODE_INFO_FILE)
    return node


def vectorinfo(node):
    dict = {}
    dict['allvector'] = read_dict_file(PATH_CFG, VECTOR_FILE)
    dict['nodevectorlen'] = len(dict['allvector'])
    print(dict['allvector'])
    dict['nodevector'] = dict['allvector'][node]
    dict['nodehashvector'] = thishash(dict['nodevector'])
    return dict

def prevhash( now_atom):
    now_atom = now_atom-1  #номер нужного файла для хеша
    with open('chain/' + str(now_atom) + '.atm', 'rb') as f:
        dict = pickle.load(f)
    hash_prev = hashlib.sha256(str(dict).encode()).digest()
    hash_prev = binascii.hexlify(hash_prev).decode('ascii')
    return hash_prev

def thishash(dict):
    hash = hashlib.sha256(str(dict).encode()).digest()
    hash = binascii.hexlify(hash).decode('ascii')
    return hash