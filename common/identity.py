import sqlite3 as db
from config import CONFIG
from Keyring import Keyring, CreateKeyspec
from key.Key import Key
import os
import random
from Crypto.Cipher import AES
from utils import hasher, ReadEntropy, packTime
#from pgp import CreateGPGKey

def CreateIdentity(password,label):
    IV = ''.join(chr(random.randint(0, 0xFF)) for i in range(16))
    mode = AES.MODE_CBC
    stash = hasher(password)
    cryptor = AES.new(stash, mode, IV=IV)
    entropy = ReadEntropy()
    ent = cryptor.encrypt(entropy)
    m = Key.fromEntropy(entropy)
    fp = hasher(m.Fingerprint())[0:6]
    data = []
    filename = CONFIG['DataDir'] + 'keyring.dat'
    with db.connect(filename) as keyring:
        cur = keyring.cursor()
        cur.execute("INSERT INTO Identity    (label, entropy, iv, fingerprint, version, created)   VALUES (?, ?, ?, ?, ?, ?)", (buffer(label),buffer(ent), buffer(IV), buffer(fp), CONFIG['Version'], buffer(packTime())))
        cur.execute("SELECT id FROM Identity    WHERE entropy=?", (buffer(ent),))
        data = cur.fetchone()
    #CreateGPGKey(identity_id=data[0], password=password, label=label, primary=True)

def ListIdentities():
    items = []
    filename = CONFIG['DataDir'] + 'keyring.dat'
    with db.connect(filename) as keyring:
        cur = keyring.cursor()
        sql = """SELECT id, label,fingerprint,created FROM Identity"""
        cur.execute(sql)
        data = cur.fetchall()
        for row in data:
            items.append({ 'id' : row[0], 'label' : row[1], 'fingerprint' : row[2], 'created' : row[3] })
    return items

def SignMessage(password,message,identity_id):
    keyspec = CreateKeyspec(False)
    filename = CONFIG['DataDir'] + 'keyring.dat'
    with db.connect(filename) as keyring:
        cur = keyring.cursor()
        sql = """ INSERT INTO Signature (keyspec,identity_id) VALUES (?, ?)"""
        cur.execute(sql, (keyspec,identity_id))
        idkey = Keyring(password,identity_id).FromKeyspec(keyspec)
    import binascii
    msg = idkey.Sign(message)
    return msg

def VerifyMessage(password,identity_id,sig,message,origin_address):
    idkey = Keyring(password,identity_id).FromKeyspec('m')
    return idkey.Verify(sig,message,origin_address)

def InitializeKeyStore(args):
    if not os.path.exists(CONFIG['DataDir']):
        os.makedirs(CONFIG['DataDir'])
    filename = CONFIG['DataDir'] + 'keyring.dat'
    init = os.path.isfile(filename)         # initialize the database if needed
    with db.connect(filename) as keyring:
        cur = keyring.cursor()
        if not init:
            initializationScript = """
              CREATE TABLE Identity    (
                                            id              INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
                                            label           TEXT    NOT NULL UNIQUE,
                                            entropy         TEXT    NOT NULL UNIQUE,
                                            iv              TEXT    NOT NULL,
                                            fingerprint     TEXT    NOT NULL, 
                                            version         INTEGER NOT NULL,
                                            created         INTEGER NOT NULL
                                        );
              CREATE TABLE Signature    (
                                            id              INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
                                            keyspec         TEXT    NOT NULL,
                                            identity_id     INTEGER NOT NULL DEFAULT 1
                                        );
              CREATE TABLE RSAKey       (
                                            id              INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
                                            keyspec         TEXT    NOT NULL,
                                            label           TEXT    NOT NULL,
                                            identity_id     INTEGER NOT NULL DEFAULT 1
                                        );
              CREATE TABLE Web          ( 
                                            id              INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
                                            domain          TEXT    NOT NULL,
                                            keyspec         TEXT    NOT NULL,
                                            created         TEXT    NOT NULL,
                                            pubkey          TEXT    NULL,
                                            expires         TEXT    NULL,
                                            username        TEXT    NULL,
                                            identity_id     INTEGER NOT NULL DEFAULT 1
                                        );
              CREATE TABLE Wallet       (
                                            id              INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
                                            currency        TEXT    NOT NULL,
                                            testnet         INTEGER NOT NULL DEFAULT 0,
                                            keyspec         TEXT    NOT NULL,
                                            identity_id     INTEGER NOT NULL DEFAULT 1
                                        );
              CREATE TABLE Address      ( 
                                            id              INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
                                            wallet_id       INTEGER NOT NULL,
                                            keyspec         TEXT    NOT NULL
                                        );
              CREATE TABLE Personal     ( 
                                            id              INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
                                            identity_id     INTEGER NOT NULL,
                                            key             TEXT    NOT NULL,
                                            value           BLOB    NOT NULL
                                        );
              CREATE TABLE Shared       ( 
                                            id              INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
                                            identity_id     INTEGER NOT NULL,
                                            personal_id     INTEGER NOT NULL,
                                            created         INTEGER NOT NULL,
                                            expires         INTEGER NOT NULL
                                        );
              """ 
            cur.executescript(initializationScript)
            CreateIdentity(args.password,'My first 1Ring Identity')
