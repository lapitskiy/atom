import redis
import pickle

class Explorer:

    def load_atom_data(self,num,atom_system_file):
        r = redis.StrictRedis(host='localhost', db=0)
        atom_file_data = {}
        if int(atom_system_file['count']) < num:
            num = atom_system_file['count']
        for i in range(0,int(atom_system_file['count'])+1):
            if atom_system_file['count'] >= num:
                current_atom_block = self.read_current_atom(i)
                atom_file_data[i] = current_atom_block
            else:
                return atom_file_data
        return atom_file_data

    def read_system_file(self, path,filename):
        with open(path+filename, 'rb') as f:
            dict = pickle.load(f)
        return dict

    def read_current_atom(self, num):
        with open('chain/' + str(num) + '.atm', 'rb') as f:
            dict = pickle.load(f)
        return dict


    def modify_to_browser(self, dict):
        #for key, value in dict.items():
           # for key2, value2 in dict[key].items():
             #   try:
            #        for key3, value3 in dict[key][key2].items():
             #   except AttributeError:
              #      continue

        return dict
