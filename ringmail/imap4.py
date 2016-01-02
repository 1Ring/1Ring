from twisted.internet import protocol
from twisted.mail import imap4
from twisted.mail.imap4 import LOGINCredentials, PLAINCredentials
from zope.interface import implements
from twisted.cred.portal import IRealm
from twisted.cred import portal

class IMAPServerProtocol(imap4.IMAP4Server):
    "Subclass of imap4.IMAP4Server that adds debugging."
    debug = True

    def lineReceived(self, line):
        if self.debug:
            print "CLIENT:", line
        imap4.IMAP4Server.lineReceived(self, line)

    def sendLine(self, line):
        imap4.IMAP4Server.sendLine(self, line)
        if self.debug:
            print "SERVER:", line

class IMAPFactory(protocol.Factory):
    def __init__(self, *a, **kw):
        self.protocol = IMAPServerProtocol
        self.portal = None # placeholder

    def buildProtocol(self, address):
        p = self.protocol()
        p.portal = self.portal
        p.factory = self
        return p

class UserAccount:
    def __init__(self):
        pass

class IMAPRealm(object):
    implements(portal.IRealm)
    avatarInterfaces = {
        imap4.IAccount: UserAccount,
    }

    def __init__(self, cache):
        self.cache = cache

    def requestAvatar(self, avatarId, mind, *interfaces):
        for requestedInterface in interfaces:
            if self.avatarInterfaces.has_key(requestedInterface):
                # return an instance of the correct class
                avatarClass = self.avatarInterfaces[requestedInterface]
                avatar = avatarClass(self.cache)
                # null logout function: take no arguments and do nothing
                logout = lambda: None
                return defer.succeed((requestedInterface, avatar, logout))

        # none of the requested interfaces was supported
        raise KeyError("None of the requested interfaces is supported")
