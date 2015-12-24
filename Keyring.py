import os
import sqlite3 as db
import binascii
import hashlib
import random
import common.utils
import struct
from key.Key import Key, _HARDEN
from Crypto.Cipher import AES
from config import CONFIG
from common.utils import hasher
from key.coins import COINS

def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in xrange(0, len(l), n):
        yield l[i:i+n]

def CreateKeyspec():
    import random
    final = []
    for x in range(0,6):
        leaf = random.randrange(int(0x000000),int(0xFFFFFF))
        final.append(struct.pack("<L",leaf))
    return buffer(''.join(final))

class Keyring(object):
    def __init__(self, password, id):
        self._cache = {}
        mode = AES.MODE_CBC

        filename = CONFIG['DataDir'] + 'keyring.dat'
        with db.connect(filename) as keyring:
            cur = keyring.cursor()
            cur.execute("SELECT entropy,iv,fingerprint FROM Identity WHERE id=?;", (id,))
            row = cur.fetchone()
            if row is None:
                self._valid = False
            else:
                cryptor = AES.new(hasher(password), mode, IV=row[1])
                self.Entropy = cryptor.decrypt(row[0])
                m = Key.fromEntropy(self.Entropy)
                # Password is invalid
                self._valid = buffer(hasher(m.Fingerprint())[0:6]) == buffer(row[2])
                assert self._valid

    def isValid(self):
        return self._valid

    def FromKeyspec(self, keyspec, coin='1Ring', testnet=False, input_type='', input_data=''):
        key = None
        acc = ''
        self.coin = coin
        self.testnet = testnet

        public = False
        key = Key.fromEntropy(entropy=self.Entropy, public=public, coin=self.coin, testnet=self.testnet)
        if keyspec == 'm':
            return key
        if testnet:
            net = 'test'
        else:
            net = 'main'
        if input_type == COINS[coin][net]['xkeyprv'] or \
           input_type == COINS[coin][net]['xkeypub']:
            key = Key.fromExtendedKey(input_data, coin=coin)
        _keyspec = list(chunks(keyspec,4))
        for x in range(0,len(_keyspec)):
            node = struct.unpack("<L",_keyspec[x])[0]
            key = key.ChildKey(node + _HARDEN)
        return key

if __name__ == "__main__":
    m_key = Keyring('This is my password.  There are many like it but this one is mine.', 1).FromKeyspec("m")
    m_key.dump()
    M_key = Keyring('This is my password.  There are many like it but this one is mine.', 1).FromKeyspec("M")
    M_key.dump()
    keyspec = []
    import random
    for x in range(0,6):
        leaf = random.randrange(int(0x000000),int(0xFFFFFF))
        keyspec.append(leaf)
        M_key = M_key.ChildKey(leaf)
        print "Keyspec: %s" % keyspec
        M_key.dump()
