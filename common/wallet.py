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
import sys
from key.coins import COINS

def CreateWallet(password, coin,testnet,identity):
    keyspec = CreateKeyspec()
    filename = CONFIG['DataDir'] + 'keyring.dat'
    with db.connect(filename) as keyring:
        cur = keyring.cursor()
        sql = """ INSERT INTO Wallet (currency,keyspec,identity_id, testnet) VALUES (?, ?, ?, ?)"""
        if testnet is True:
            tn=1
        else:
            tn=0
        cur.execute(sql, (coin, keyspec, identity, tn))
    print Keyring(password,identity).FromKeyspec(keyspec,coin,testnet).WalletImportFormat()

def ListWallets(password, identity):
    items = []
    filename = CONFIG['DataDir'] + 'keyring.dat'
    with db.connect(filename) as keyring:
        cur = keyring.cursor()
        sql = """SELECT id, currency, testnet FROM Wallet WHERE identity_id = ?"""
        cur.execute(sql, str(identity))
        data = cur.fetchall()
        for row in data:
            items.append({ 'id' : row[0], 'currency' : row[1], 'balance' : GetWalletBalance(password,identity,row[0]), 'testnet': (row[2]==1) })
    return items

def ListAddresses(password, identity, wallet_id):
    items = []
    filename = CONFIG['DataDir'] + 'keyring.dat'
    with db.connect(filename) as keyring:
        cur = keyring.cursor()
        sql = """SELECT keyspec,currency,testnet FROM Wallet WHERE id=? AND identity_id=?"""
        cur.execute(sql, (str(wallet_id),str(identity)))
        row = cur.fetchone()
        if row is None:
            print "No wallets defined."
            sys.exit(0)
        KR = Keyring(password,identity)
        # Load wallet info
        wallet = KR.FromKeyspec(keyspec=str(row[0]),coin=str(row[1]),testnet=int(row[2])==1)
        if wallet.network=='test':
            net = 'test'
        else:
            net = 'main'
        sql = """SELECT Address.keyspec,Address.id,currency,testnet FROM Address, Wallet WHERE wallet_id = ? AND Wallet.id=wallet_id"""
        cur.execute(sql, (str(wallet_id),))
        data = cur.fetchall()
        for item in data:
            new_key = KR.FromKeyspec(keyspec=str(item[0]),coin=str(wallet.coin),testnet=(wallet.network=='test'), input_type=COINS[wallet.coin][net]['xkeyprv'], input_data=wallet.ExtendedKey(True))
            address = new_key.Address()
            items.append([address,wallet.coin,GetAddressBalance(wallet.coin, address),item[1]])
        return items

def GetAddressBalance(coin,address):
    import requests
    if coin=='bitcoin':
        url = 'http://btc.blockr.io/api/v1/address/balance/' + address
    if coin=='litecoin':
        url = 'http://ltc.blockr.io/api/v1/address/balance/' + address
    if coin=='unobtanium':
        url = 'https://chainz.cryptoid.info/uno/api.dws?q=getbalance&a=' + address
        response = requests.get(url)
        data = response.text
        balance = int(data)
    elif coin=='ethereum':
        pass
    elif coin=='expanse':
        pass
    else:
        response = requests.get(url)
        data = response.json()
        assert data['status'] == 'success'
        balance = data['data']['balance'] + data['data']['balance_multisig']
    return balance    

def GenerateAddress(password, identity, wallet_id):
    filename = CONFIG['DataDir'] + 'keyring.dat'
    with db.connect(filename) as keyring:
        cur = keyring.cursor()
        sql = """SELECT keyspec,currency,testnet FROM Wallet WHERE id=? AND identity_id=?"""
        cur.execute(sql, (str(wallet_id),str(identity)))
        row = cur.fetchone()
        if row is None:
            print "No wallets defined."
            sys.exit(0)
        KR = Keyring(password,identity)
        # Load wallet info
        wallet = KR.FromKeyspec(keyspec=str(row[0]),coin=str(row[1]),testnet=int(row[2])==1)
        # Generate a new keyspec
        keyspec = CreateKeyspec()
        # From the wallet xprv, generate the keypair at the keyspec
        if wallet.network=='test':
            net = 'test'
        else:
            net = 'main'
        new_key = KR.FromKeyspec(keyspec=keyspec,coin=str(wallet.coin),testnet=(wallet.network=='test'), input_type=COINS[wallet.coin][net]['xkeyprv'], input_data=wallet.ExtendedKey(True))
        sql = """ INSERT INTO Address (wallet_id,keyspec) VALUES (?, ?)"""
        cur.execute(sql, (wallet_id,keyspec,))
        print new_key.Address()

def GetWalletBalance(password, identity, wallet):
    import requests
    filename = CONFIG['DataDir'] + 'keyring.dat'
    coin = ""
    url = ""
    with db.connect(filename) as keyring:
        cur = keyring.cursor()
        sql = """SELECT Address.keyspec,Wallet.keyspec,currency,testnet FROM Address, Wallet WHERE wallet_id = ? AND Wallet.id=wallet_id"""
        cur.execute(sql, (str(wallet),))
        data = cur.fetchall()
        snd = ""
        KR = Keyring(password,identity)
        # Load wallet info
        if len(data) == 0:
            return False
        this_wallet = KR.FromKeyspec(keyspec=str(data[0][1]),coin=str(data[0][2]),testnet=int(data[0][3])==1)
        for row in data:
            if this_wallet.network=='test':
                net = 'test'
            else:
                net = 'main'
            new_key = KR.FromKeyspec(keyspec=str(row[0]),coin=str(this_wallet.coin),testnet=(this_wallet.network=='test'), input_type=COINS[this_wallet.coin][net]['xkeyprv'], input_data=this_wallet.ExtendedKey(True))
            snd += new_key.Address() + ","
        snd = snd[0:-1]
        if this_wallet.coin=='bitcoin':
            url = 'http://btc.blockr.io/api/v1/address/balance/' + snd
        if this_wallet.coin=='litecoin':
            url = 'http://ltc.blockr.io/api/v1/address/balance/' + snd
        if this_wallet.coin=='unobtanium':
            li = snd.split(',')
            balance = 0
            for i in li:
                url = 'https://chainz.cryptoid.info/uno/api.dws?q=getbalance&a=' + i 
                response = requests.get(url)
                data = response.text
                balance += int(data)
        elif this_wallet.coin == 'ethereum' or this_wallet.coin=='expanse':
            balance = 0
        else:
            response = requests.get(url)
            data = response.json()
            assert data['status'] == 'success'
            balance = 0
            for i in data[u'data']:
                if str(i) == 'balance' or str(i) == 'balance_multisig' :
                    balance += data['data']['balance'] + data['data']['balance_multisig']
                elif str(i) != 'address':
                    balance += i[u'balance'] + i[u'balance_multisig']
        return balance