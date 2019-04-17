import pickle
import os

class Server:

    def read_dict_file(self,path,filename):
        with open(path+filename, 'rb') as f:
            dict = pickle.load(f)
        return dict

    def load_poh_active(self):
        dict = self.read_dict_file('chain/config/','nodeinfo.atm')
        return dict['poh_active']

    # количество нод в данной ноде
    def rnd_node_ip(self,node_id, rnd_node):
        path = 'chain/config/'
        filename = 'node_vector.atm'
        result = self.read_dict_file(path, filename)
        node_vector = result[node_id]
        return node_vector[rnd_node]['ipport']

    # проверка lake файла на наличие транзакций
    def test_empty_lake_file(self):
        if os.stat("chain/config/txpool_leak.atm").st_size == 0:
            check = True
        else:
            check = False
        return check













