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

from pyme import core, callbacks
from keyring import Keyring, CreateKeyspec
import sqlite3 as db
from config import CONFIG
from utils import hasher
from datetime import date
import binascii 

def CreateGPGKey(identity_id, password, label='', primary=False):
    # Initialize our context.
    core.check_version(None)

    c = core.Context()
    c.set_armor(1)
    c.set_progress_cb(callbacks.progress_stdout, None)
    print identity_id
    print password
    primary_id = Keyring(password,identity_id).FromKeyspec('m')  
    if primary:
        gpg_id = primary_id
        id_str = "(0x%s, Primary)" % binascii.hexlify((hasher(gpg_id.Fingerprint())[0:6]))
    else:
        keyspec = CreateKeyspec()
        gpg_id = Keyring(password,identity_id).FromKeyspec(keyspec)    
        id_str = "(0x%s)" % binascii.hexlify((hasher(gpg_id.Fingerprint())[0:6]))
        sql = """INSERT INTO RSAKey (keyspec,label,identity_id) VALUES (?, ?, ?)"""
        filename = CONFIG['DataDir'] + 'keyring.dat'
        with db.connect(filename) as keyring:
            cur = keyring.cursor()
            cur.execute(sql, (keyspec, buffer(label), identity_id))
    parms = """<GnupgKeyParms format="internal">
    Key-Type: DSA
    Key-Length: 1024
    Subkey-Type: ELG-E
    Subkey-Length: 1024
    Name-Real: 1Ring Identity %s 
    Name-Comment: Not all who wander are lost.
    Name-Email: %s@firewall.1ring.io
    Passphrase: %s
    Expire-Date: %s-12-21
    </GnupgKeyParms>
    """ % (id_str, gpg_id.Address(), binascii.hexlify(gpg_id.PrivateKey()), date.today().year+2)
    c.op_genkey(parms, None, None)
    print c.op_genkey_result().fpr
