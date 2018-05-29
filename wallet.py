import ecdsa
import binascii
import hashlib
import base58
import redis
from decimal import Decimal,getcontext
getcontext().prec = 7

import os
from uuid import uuid4
from argon2 import PasswordHasher
import urllib3

class Wallet:
# SECP256k1 elliptic curve
# make cookie wallet
    def __init__(self):
        self.private_key = []
        self.public_key = []

    def b58_key(self,key):
        key = binascii.hexlify(key.to_string()).decode('ascii')
        return key

    def b58_key_encode(self,key):
        key = base58.b58encode(bytes.fromhex(key))
        return key

    def public_key_to_adress(self,key):
        ripemd160 = hashlib.new('ripemd160')
        ripemd160.update(hashlib.sha256(key.encode()).digest())
        key = base58.b58encode(ripemd160.digest())
        return key

    def b58_key_decode(self,key):
        key = base58.b58decode(key).hex()
        return key

    @staticmethod
    def write_new_wallet(wfc):
        with open('wallet.pem', 'w') as out:
            for key, val in wfc.items():
                out.write('{}:{}\n'.format(key, val))

    def read_wallet(self,wallet_data):
        item = eval(wallet_data)
        # item = dict(item.split(':') for item in wallet_data.split())
        return item

    def pass_hash(self,pwd):
        # Победитель Password Hashing Competition Argon2 https://habrahabr.ru/post/281569/
        ph = PasswordHasher()
        pwd_hash = ph.hash(pwd)
        return pwd_hash

    def pass_verify(self,pwd,hash):
        ph = PasswordHasher()
        something = 'pass wrong'
        try:
            val = ph.verify(hash, pwd)
        except:
            return something
        return bool(val)

    def generate_key(self):
        generate_key = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
        public_key = generate_key.get_verifying_key() # clear key: <ecdsa.keys.SigningKey object at 0x06521A30>
        public_key = public_key.to_string().hex()
        private_key = binascii.hexlify(generate_key.to_string()).decode() #privat key: 374bc766d11a59a826249fc42f370cee0518e70925c96e73c1848716216d2f64
        return (private_key, public_key)

    def generate_sig(self, prkey, msg):
        unhex = binascii.unhexlify(prkey)  # unhex privat key clear: b'7K\xc7f\xd1\x1aY\xa8&$\x9f\xc4/7\x0c\xee\x05\x18\xe7\t%\xc9ns\xc1\x84\x87\x16!m/d'
        sign_msg = ecdsa.SigningKey.from_string(unhex, curve=ecdsa.SECP256k1)
        msg = str(msg).encode()
        sig = sign_msg.sign(msg)
        sig = sig.hex()
        return sig


    def verify_sig(self, pbkey, sign, msg):
        verify_key = ecdsa.VerifyingKey.from_string(bytes.fromhex(pbkey), curve=ecdsa.SECP256k1)
        try:
            msg = str(msg).encode()
            verify = verify_key.verify(bytes.fromhex(sign), msg)
        except ecdsa.BadSignatureError:
            verify = False
        return verify


