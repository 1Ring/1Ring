#!/usr/bin/env python
#
# Copyright (c) Twisted Matrix Laboratories.
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

from zope.interface import implements

from twisted.internet import defer

from twisted.cred.credentials import IUsernamePassword
from twisted.cred.checkers import ICredentialsChecker
from twisted.cred.portal import Portal
from common.utils import checkAddress
from key.Key import Key
from key.coins import COINS
from ringmail.pop3 import *
from ringmail.imap4 import *
from ringmail.smtp import *

import key.Base58
import hashlib

class ObjCache(object):
  def __init__(self):
    self.cache = {}

  def get(self, item):
    return self.cache[item]

  def set(self, item, value):
    self.cache[item] = value

class PasswordChecker:
    implements(ICredentialsChecker)
    credentialInterfaces = (IUsernamePassword,)

    def __init__(self, password):
        "passwords: a string object containing the base for signatures"
        self.verify_message = password

    def requestAvatarId(self, credentials):
        username = credentials.username
        password = credentials.password
        if checkAddress(username):
            pubkey = Key.RecoverPubkey(self.verify_message,password)
            vh160 = COINS['1Ring']['main']['prefix'].decode('hex')+hashlib.new('ripemd160', sha256(pubkey).digest()).digest()
            check_addr=Base58.check_encode(vh160)
            if check_addr == username:
                if Key.Verify(password,self.verify_message,username):
                    return defer.succeed(username)
                else:
                    return defer.fail(
                        credError.UnauthorizedLogin("Bad password"))
            else:
                return defer.fail(
                    credError.UnauthorizedLogin("Bad password"))
        else:
            return defer.fail(
                credError.UnauthorizedLogin("No such user"))

def main():
    from twisted.application import internet
    from twisted.application import service    
    from twisted.internet.protocol import ServerFactory

    myURL = "firewall.1ring.io"

    checker = PasswordChecker(myURL)    

    smtp_portal = Portal(SMTPRealm(), [checker])
    imap_portal = Portal(IMAPRealm(ObjCache()), [checker])
    pop3_portal = Portal(POP3Realm(), [checker])
    
    a = service.Application("1Ring SMTP/IMAP Server")
    internet.TCPServer(2500, SMTPFactory(smtp_portal)).setServiceParent(a)
    internet.TCPServer(1143, IMAPFactory(imap_portal)).setServiceParent(a)
    internet.TCPServer(1230, POP3Factory(pop3_portal)).setServiceParent(a)    

    return a

application = main()