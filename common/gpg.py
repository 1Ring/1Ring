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
