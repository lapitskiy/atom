from wallet import *
from baking import *
import requests
from flask import Flask, jsonify, request, render_template, redirect, make_response
from decimal import Decimal, getcontext
from cl_node import *
getcontext().prec = 7


# Instantiate the Node
app = Flask(__name__)
# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')
wallet = Wallet()  # Создаем объект кошелька
dbatom = Baking()  # Создаем объект готовки печенья
node = Node()

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/baking', methods=['GET'])
def baking():
    # задаем параметры базы redis: находится на localhost, стандартный порт 6379, номер базы 1
    dbatom.clear(0)
    data = dbatom.baking(0)
    size = dbatom.size(0)
    response = {
        'size': size,
        'data': data
               }
    return jsonify(response), 200


@app.route('/newwallet', methods=['GET'])
def new_wallet():
    return render_template('newwallet.html')

@app.route('/zalypa', methods=['GET'])
def zalypa():
    # r = redis.StrictRedis(host='localhost', db=2)
    # r.flushdb()
    # r.rpush('1', 'zalypa')
    # r.rpush('1', 'zalypa2')--
    # r.rpush('1', 'zalypa3')
    # r.rpush('1', 'zalypa')
    # r.rpush('1', 'zalypa4')
    # r.rpush('1', 'zalypa')
    # data = r.lrange('1', 0, -1)
    # print(data)
    # r.lrem('1',0,'zalypa')
    # data = r.lrange('1', 0, -1)
    # print(data)
    data = 0x08
    print(str(data))
    print(chr(data).encode())




@app.route('/makewallet', methods=['POST'])
def make_wallet():
    # We run make new wallet
    # generate pb[1] and pr[0] key
    get_two_key = wallet.generate_key()
    # кодируем public ключ, чтобы сделать его короче

    public_key_encode = wallet.b58_key_encode(get_two_key[1])
    public_key_adress = wallet.public_key_to_adress(public_key_encode)

    # encrypting a password...
    wallet_pass = wallet.pass_hash(format(request.form['text']))
    # пишем в файл ключ-значение
    wallet_file_content = {
            "privatkey_clear": get_two_key[0],
            "publickey_clear": get_two_key[1],
            "publickey_encode": public_key_encode,
            "publickey_adress": public_key_adress,
            "pwd": wallet_pass}
    wallet.write_new_wallet(wallet_file_content)
    response = make_response(str(wallet_file_content))
    response.headers["Content-Disposition"] = "attachment; filename=result.pem"
    return response




@app.route('/openwallet', methods=['GET', 'POST'])
def open_and_varify_file():
    if request.method == 'POST':
        # check if the post request has the file part
        # encrypting a password...
        if 'file' not in request.files:
            print('No file part')
            return redirect(request.url)
        file = request.files.get('file')
        if file.filename == '':
            print('No selected file')
            return redirect(request.url)

        if file:
            wallet_data = wallet.read_wallet(file.stream.read().decode("utf-8"))
            # wallet_data['privatkey_clear'] = wallet_data['privatkey_clear'].decode("utf-8") #bytes to str
            pass_verify = wallet.pass_verify(format(request.form['password_wallet']), wallet_data['pwd'])


            if pass_verify==True:
                r = redis.StrictRedis(host='localhost', db=0)

                r_len = r.dbsize()
                atom_count = 0
                atom_sum = 0
                data = {}
                data_info = {}
                owner_count = {}
                owner_tobig_data = {}
                owner_adr  = {}
                ji = 0
                #перебираем всю цепочку владельцев внутри одного атома
                for i in range(0, r.dbsize()):
                    h = 0
                    h2 = 0
                    data_2 = {}
                    for j in range(0,r.llen(i)):
                        data_2[h2] = r.lindex(i,j).decode()
                        h2 += 1
                        if j % 2 == 0:
                            if r.lindex(i,j).decode() == wallet_data['publickey_adress']:
                                h += 1
                                atom_count += 1
                                atom_sum = atom_sum + Decimal(r.lindex(i, j + 1).decode())
                                # owner_count[h] = {r.lindex(i, j).decode(): r.lindex(i, j + 1).decode()}
                                owner_adr[h]= {r.lindex(i,j).decode():r.lindex(i,j+1).decode()}
                                data_info[i] = dict(owner_adr)
                    data[i]= data_2
                return render_template('verifywallet.html', verify=pass_verify, wallet_data=wallet_data, count2=atom_count, atom_sum=atom_sum, data=data, data_adr=data_info, len=r_len)
            else:
                return render_template('takewallet.html', verify=pass_verify)

    return render_template('takewallet.html')


@app.route('/ajax_get_main', methods=['GET', 'POST'])
def ajax_test():
    dict = {}
    msg = {}
    dict['send_wallet'] = request.args.get('send_wallet', 0, type=str)
    dict['send_atom'] = request.args.get('send_atom', 0, type=float)
    dict['atom_sum'] = request.args.get('atom_sum', 0, type=float)
    komis = Decimal(dict['send_atom']) / Decimal(100)
    dict['send_komis'] = str(komis.normalize())
    dict['verify'] = request.args.get('verify', 0, type=str)
    dict['privatkey_clear'] = request.args.get('privatkey_clear', 0, type=str)
    dict['publickey_clear'] = request.args.get('publickey_clear', 0, type=str)
    dict['publickey_adress'] = request.args.get('publickey_adress', 0, type=str)

    if dict['atom_sum'] < dict['send_atom']:
        dict['result'] = 'На счету не хватает такой суммы'
        return jsonify(result=dict)
    if dict['send_wallet'] == dict['publickey_adress']:
        dict['result'] = 'Вы пытаетесь отправить сами себе'
        return jsonify(result=dict)

    if dict['send_wallet'] != '' and dict['send_atom'] != '' and dict['atom_sum'] >= dict['send_atom']:
        node_url = 'http://localhost:5001/connect'
        msg = {'from': dict['send_wallet'], 'from_pbkey': dict['publickey_clear'], 'count': str(dict['send_atom']),'send': dict['publickey_adress'], 'send_komis':dict['send_komis']}
        msg['thishash'] = node.thishash(msg)
        msg['sign'] = wallet.generate_sig(dict['privatkey_clear'], msg)
        response = requests.post(node_url, data=msg)
        dict['result'] = response.text
    return jsonify(result=dict)

if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5002, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='0.0.0.0', port=port)