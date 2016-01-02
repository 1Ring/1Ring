from twisted.internet import protocol
from twisted.mail.pop3 import IMailbox
from zope.interface import implements
from twisted.cred.portal import IRealm

class POP3Mailbox:
    implements(IMailbox)

    def __init__(self):
        message = """From: me
To: you
Subject: A test mail

Hello world!"""
        self.messages = [m for m in repeat(message, 20)]


    def listMessages(self, index=None):
        if index != None:
            return len(self.messages[index])
        else:
            return [len(m) for m in self.messages]

    def getMessage(self, index):
        return StringIO(self.messages[index])

    def getUidl(self, index):
        return md5(self.messages[index]).hexdigest()

    def deleteMessage(self, index):
        pass

    def undeleteMessages(self):
        pass

    def sync(self):
        pass

class POP3Factory(protocol.Factory):
    def __init__(self, *a, **kw):
        from twisted.mail import pop3
        self.protocol = pop3.POP3
        self.portal = None # placeholder

    def buildProtocol(self, address):
        p = self.protocol()
        p.portal = self.portal
        p.factory = self
        return p

class POP3Realm:
    implements(IRealm)

    def requestAvatar(self, avatarId, mind, *interfaces):
        if IMailbox in interfaces:
            return IMailbox, SimpleMailbox(), lambda: None
        else:
            raise NotImplementedError()

