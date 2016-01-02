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

import time, binascii
from datetime import datetime
from math import log,pow,floor
import hashlib
import sys
import random
import os
import key.Base58
import sqlite3 as db
from key import Key
from Crypto.Cipher import AES
from config import CONFIG
import struct

def hasher(string):
    for x in range(0,50000):
        string = hashlib.sha256(string).digest()
    return string

def packTime(_time=time.time()):
    return binascii.unhexlify(str(int(time.mktime(time.gmtime(_time))) - time.timezone))

def unpackTime(_time):
    return datetime.utcfromtimestamp(int(binascii.hexlify(_time)))

def checkAddress(bc):
    addr = Base58.b58decode(bc,25)
    if addr is None: return None
    version = addr[0]
    checksum = addr[-4:]
    vh160 = addr[:-4] # Version plus hash160 is what is checksummed                                                                                                    
    h3=sha256(sha256(vh160).digest()).digest()
    if h3[0:4] == checksum:
        return True
    else:
        return False

char_set = {'small': 'abcdefghijklmnopqrstuvwxyz',
             'nums': '0123456789',
             'big': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
             #'special': '^!\$%&/()=?{[]}+~#-_.:,;<>|\\'
             'special': '!$%^&*()_+=-,.<>'
            }


def ReadEntropy():
    count = CONFIG['EntropyBits']/8
    entropy = os.urandom(count)
    if len(entropy) < CONFIG['EntropyBits']/8:
        raise Exception("Insufficient entropy provided")
    return entropy

def generate_password(length=21, _seed=None):
    """Function to generate a password"""
    def check_prev_char(password, current_char_set):
        """Function to ensure that there are no consecutive 
        UPPERCASE/lowercase/numbers/special-characters."""

        index = len(password)
        if index == 0:
            return False
        else:
            prev_char = password[index - 1]
            if prev_char in current_char_set:
                return True
            else:
                return False
    password = []
    if _seed is None:
        _seed = time.time()
    random.seed(_seed)
    while len(password) < length:
        key = random.choice(char_set.keys())
        a_char = str(random.random()).replace(".","").replace("e-","")
        test_char = a_char[2:5]
        if 0 <= int(test_char) <= 255:
            if chr(int(test_char)) in char_set[key]:
                if check_prev_char(password, char_set[key]):
                    continue
                else:
                    password.append(chr(int(test_char)))
    return ''.join(password)

# Written by Arno Bakker
# see LICENSE.txt for license information
""" 
Reference Implementation of Merkle hash torrent extension, as now 
standardized in http://www.bittorrent.org/beps/bep_0030.html (yay!)
"""

DEBUG = False

# External classes

class MerkleTree:
    
    def __init__(self,total_length,root_hash=None,hashes=None):
        self.npieces = total_length
        self.treeheight = get_tree_height(self.npieces)
        self.tree = create_tree(self.treeheight)
        if hashes is None:
            self.root_hash = root_hash
        else:
            fill_tree(self.tree,self.treeheight,self.npieces,hashes)
            # root_hash is None during .torrent generation
            if root_hash is None:
                self.root_hash = self.tree[0]
            else:
                raise AssertionError, "merkle: if hashes not None, root_hash must be"

    def get_root_hash(self):
        return self.root_hash

    def compare_root_hashes(self,other):
        return self.root_hash == other

    def get_hashes_for_piece(self,index):
        return get_hashes_for_piece(self.tree,self.treeheight,index)

    def check_hashes(self,hashlist):
        return check_tree_path(self.root_hash,self.treeheight,hashlist)

    def update_hash_admin(self,hashlist,piece_hashes):
        update_hash_admin(hashlist,self.tree,self.treeheight,piece_hashes)

    def get_piece_hashes(self):
        """
        Get the pieces' hashes from the bottom of the hash tree. Used during
        a graceful restart of a client that already downloaded stuff.
        """
        return get_piece_hashes(self.tree,self.treeheight,self.npieces)

def create_fake_hashes(info):
    total_length = calc_total_length(info)
    npieces = total_length
    return ['\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' ] * npieces


# Internal functions
# Design choice: all algoritmics have been returned into stateless functions,
# i.e. they operate on the input parameters only. This to keep them extremely
# clear.

def calc_total_length(info):
    # Merkle: Calculate total length from .torrent info
    if info.has_key('length'):
        return info['length']
    # multi-file torrent
    files = info['files']
    total_length = 0
    for i in range(0,len(files)):
        total_length += files[i]['length']
    return total_length


def get_tree_height(npieces):
    if DEBUG:
        print >> sys.stderr,"merkle: number of pieces is",npieces
    height = log(npieces,2)
    if height - floor(height) > 0.0:
        height = int(height)+1
    else:
        height = int(height)
    if DEBUG:
        print >> sys.stderr,"merkle: tree height is",height
    return height

def create_tree(height):
    # Create tree that has enough leaves to hold all hashes
    treesize = int(pow(2,height+1)-1) # subtract unused tail
    if DEBUG:
        print >> sys.stderr,"merkle: treesize",treesize
    tree = ['\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' ] * treesize
    return tree

def fill_tree(tree,height,npieces,hashes):
    # 1. Fill bottom of tree with hashes
    startoffset = int(pow(2,height)-1)
    if DEBUG:
        print >> sys.stderr,"merkle: bottom of tree starts at",startoffset
    for offset in range(startoffset,startoffset+npieces):
        #print >> sys.stderr,"merkle: copying",offset
        #print >> sys.stderr,"merkle: hashes[",offset-startoffset,"]=",str(hashes[offset-startoffset])
        tree[offset] = hashes[offset-startoffset]._hash
    # 2. Note that unused leaves are NOT filled. It may be a good idea to fill
    # them as hashing 0 values may create a security problem. However, the
    # filler values would have to be known to any initial seeder, otherwise it 
    # will not be able build the same hash tree as the other initial seeders.
    # Assume anyone should be able to autonomously become a seeder, the filler 
    # must be public info. I don't know whether having public info as filler 
    # instead of 0s is any safer, cryptographically speaking. Hence, we stick 
    # with 0 for the moment

    # 3. Calculate higher level hashes from leaves
    for level in range(height,0,-1):
        if DEBUG:
            print >> sys.stderr,"merkle: calculating level",level
        for offset in range(int(pow(2,level)-1),int(pow(2,level+1)-2),2):
            #print >> sys.stderr,"merkle: data offset",offset
            [ parentstartoffset, parentoffset ] = get_parent_offset(offset,level)
            #print >> sys.stderr,"merkle: parent offset",parentoffset                
            data = tree[offset]+tree[offset+1]
            digester = hashlib.sha256(data)
            digest = digester.digest()
            tree[parentoffset] = digest
    #for offset in range(0,treesize-1):
    #        print offset,"HASH",str(tree[offset])
    return tree


def get_hashes_for_piece(tree,height,index):
    startoffset = int(pow(2,height)-1)
    myoffset = startoffset+index
    if DEBUG:
        print >> sys.stderr,"merkle: myoffset",myoffset
    # 1. Add piece's own hash
    hashlist = [ [myoffset,tree[myoffset]] ]
    # 2. Add hash of piece's sibling, left or right
    if myoffset % 2 == 0:
        siblingoffset = myoffset-1
    else:
        siblingoffset = myoffset+1
    if DEBUG:
        print >> sys.stderr,"merkle: siblingoffset",siblingoffset
    if siblingoffset != -1:
        hashlist.append([siblingoffset,tree[siblingoffset]])
    # 3. Add hashes of uncles
    uncleoffset = myoffset
    for level in range(height,0,-1):
        uncleoffset = get_uncle_offset(uncleoffset,level)
        if DEBUG:
            print >> sys.stderr,"merkle: uncleoffset",uncleoffset
        hashlist.append( [uncleoffset,tree[uncleoffset]] )
    return hashlist


def check_tree_path(root_hash,height,hashlist):
    """
    The hashes should be in the right order in the hashlist, otherwise
    the peer will be kicked. The hashlist parameter is assumed to be
    of the right type, and contain values of the right type as well.
    The exact values should be checked for validity here.
    """
    maxoffset = int(pow(2,height+1)-2)
    mystartoffset = int(pow(2,height)-1)
    i=0
    a = hashlist[i]
    if a[0] < 0 or a[0] > maxoffset:
        return False
    i += 1
    b = hashlist[i]
    if b[0] < 0 or b[0] > maxoffset:
        return False
    i += 1
    myindex = a[0]-mystartoffset
    sibindex = b[0]-mystartoffset
    for level in range(height,0,-1):
        if DEBUG:
            print >> sys.stderr,"merkle: checking level",level
        a = check_fork(a,b,level)
        b = hashlist[i]
        if b[0] < 0 or b[0] > maxoffset:
            return False
        i += 1
    if DEBUG:
        print >> sys.stderr,"merkle: ROOT HASH",`str(root_hash)`,"==",`str(a[1])`
    if a[1] == root_hash:
        return True
    else:
        return False

def update_hash_admin(hashlist,tree,height,hashes):
    mystartoffset = int(pow(2,height)-1)
    for i in range(0,len(hashlist)):
        if i < 2:
            # me and sibling real hashes of piece data, save them
            index = hashlist[i][0]-mystartoffset
            # ignore siblings that are just tree filler
            if index < len(hashes):
                if DEBUG:
                    print >> sys.stderr,"merkle: update_hash_admin: saving hash of",index
                hashes[index] = hashlist[i][1]
        # put all hashes in tree, such that we incrementally learn it 
        # and can pass them on to others
        tree[hashlist[i][0]] = hashlist[i][1]


def check_fork(a,b,level):
    myoffset = a[0]
    siblingoffset = b[0]
    if myoffset > siblingoffset:
        data = b[1]+a[1]
        if DEBUG:
            print >> sys.stderr,"merkle: combining",siblingoffset,myoffset
    else:
        data = a[1]+b[1]
        if DEBUG:
            print >> sys.stderr,"merkle: combining",myoffset,siblingoffset
    digester = hashlib.sha256(data)
    digest = digester.digest()
    [parentstartoffset, parentoffset ] = get_parent_offset(myoffset,level-1)
    return [parentoffset,digest]

def get_parent_offset(myoffset,level):
    parentstartoffset = int(pow(2,level)-1)
    mystartoffset = int(pow(2,level+1)-1)
    parentoffset = parentstartoffset + (myoffset-mystartoffset)/2
    return [parentstartoffset, parentoffset]


def get_uncle_offset(myoffset,level):
    if level == 1:
        return 0
    [parentstartoffset,parentoffset ] = get_parent_offset(myoffset,level-1)
    if DEBUG:
        print >> sys.stderr,"merkle: parent offset",parentoffset        
    parentindex = parentoffset-parentstartoffset
    if parentoffset % 2 == 0:
        uncleoffset = parentoffset-1
    else:
        uncleoffset = parentoffset+1
    return uncleoffset

def get_piece_hashes(tree,height,npieces):
    startoffset = int(pow(2,height)-1)
    hashes = ['\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' ] * npieces
    for offset in range(startoffset,startoffset+npieces):
        hashes[offset-startoffset] = tree[offset]
    return hashes

if __name__ == '__main__':
    print generate_password(21,0xFF49E2)