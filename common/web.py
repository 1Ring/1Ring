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
