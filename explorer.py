from flask import Flask, jsonify, request, render_template, redirect, make_response
from cl_explorer import *


# Instantiate the Node
app = Flask(__name__)

explorer = Explorer()  # Создаем объект Explorer

@app.route('/explorer', methods=['GET', 'POST'])
def explorer2():
    num = 5
    atom_system_file = explorer.read_system_file('chain/config/','nodeinfo.atm')
    last_transaction = explorer.load_atom_data(num,atom_system_file)
    node_vector = explorer.read_system_file('chain/config/','node_vector.atm')
    print(node_vector)
    return render_template('explorer.html', last_transaction=last_transaction, atom_system_file=atom_system_file, node_vector=node_vector)

@app.route('/ajax_get', methods=['GET', 'POST'])
def ajax_get():
    num = 5
    atom_system_file = explorer.read_system_file()
    last_transaction = explorer.load_atom_data(num, atom_system_file)
    print(last_transaction)
    return jsonify(result=last_transaction)

if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5003, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='0.0.0.0', port=port)


