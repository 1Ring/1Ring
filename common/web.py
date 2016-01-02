#!/usr/bin/env python
#
# Copyright 2015 Alternative Systems All Rights Reserved
#
# Redistribution and use in source and binary forms, with or without 
# modification, are permitted provided that the following conditions are met:
#
# *   Redistributions of source code must retain the above copyright notice, 
#       this list of conditions and the following disclaimer. 
# *   Redistributions in binary form must reproduce the above copyright notice, 
#       this list of conditions and the following disclaimer in the 
#       documentation and/or other materials provided with the distribution. 
# *   Neither the name of the Alternative Systems LLC nor the names of its 
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
from utils import unpackTime,generate_password,packTime
import os

def ListWebsites(identity_id):
    filename = CONFIG['DataDir'] + 'keyring.dat'
    items=[]
    with db.connect(filename) as keyring:
        cur = keyring.cursor()
        sql = """SELECT id,domain,created,username FROM Web WHERE identity_id=?"""
        cur.execute(sql, (identity_id,))
        data = cur.fetchall()
        for d in data:
            items.append({ 'id' : d[0], 'domain' : d[1], 'created' : unpackTime(d[2]), 'username' : d[3] })
    return items

def CreateWebsitePassword(password, identity_id, domain_name, username):
    keyspec = CreateKeyspec()
    data = []
    filename = CONFIG['DataDir'] + 'keyring.dat'
    key = Keyring(password,identity_id).FromKeyspec(keyspec)
    with db.connect(filename) as keyring:
        cur = keyring.cursor()
        cur.execute("INSERT INTO Web    (domain, keyspec, created, username, identity_id)   VALUES (?, ?, ?, ?, ?)", (buffer(domain_name),buffer(keyspec), buffer(packTime()), username, str(identity_id)))
    return generate_password(_seed=key.PrivateKey()), "%s@firewall.1ring.io" % key.Address()[0:12]

def ShowPassword(password,identity_id,website_id):
    items = []
    filename = CONFIG['DataDir'] + 'keyring.dat'
    with db.connect(filename) as keyring:
        cur = keyring.cursor()
        sql = """SELECT keyspec,username FROM Web WHERE id=? AND identity_id=?"""
        cur.execute(sql, (str(website_id),str(identity_id)))
        row = cur.fetchone()
        if row is None:
            print "No passwords defined."
            sys.exit(0)
        KR = Keyring(password,identity_id)
        # Load wallet info
        id = KR.FromKeyspec(keyspec=str(row[0]))
        return generate_password(_seed=id.PrivateKey()), row[1], "%s@firewall.1ring.io" % id.Address()[0:12]
