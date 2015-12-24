#!/usr/bin/env python
#
# Copyright 2015 Alternative Systems All Rights Reserved
#
# Redistribution and use in source and binary forms, with or without 
# modification, are permitted provided that the following conditions are met:
#
# •   Redistributions of source code must retain the above copyright notice, 
#       this list of conditions and the following disclaimer. 
# •   Redistributions in binary form must reproduce the above copyright notice, 
#       this list of conditions and the following disclaimer in the 
#       documentation and/or other materials provided with the distribution. 
# •   Neither the name of the Alternative Systems LLC nor the names of its 
#       contributors may be used to endorse or promote products derived from 
#       this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE 
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE 
# ARE DISCLAIMED. IN NO EVENT SHALL THE ALTSYSTEM OR CONTRIBUTORS BE LIABLE FOR 
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL 
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR 
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER 
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, 
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE 
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# EXPORT LAWS: THIS LICENSE ADDS NO RESTRICTIONS TO THE EXPORT LAWS OF YOUR 
# JURISDICTION. It is licensee's responsibility to comply with any export 
# regulations applicable in licensee's jurisdiction. Under CURRENT (Dec 2015) 
# U.S. export regulations this software is eligible for export from the U.S. 
# and can be downloaded by or otherwise exported or reexported worldwide EXCEPT 
# to U.S. embargoed destinations which include Cuba, Iraq, Libya, North Korea, 
# Iran, Syria, Sudan, Afghanistan and any other country to which the U.S. has 
# embargoed goods and services.

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
