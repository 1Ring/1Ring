from twisted.mail import smtp
from twisted.internet import defer
from zope.interface import implements

class SMTPMessageDelivery:
    implements(smtp.IMessageDelivery)
    
    def receivedHeader(self, helo, origin, recipients):
        return "Received: SMTPMessageDelivery"

    def validateFrom(self, helo, origin):
        # All addresses are accepted
        return origin
    
    def validateTo(self, user):
        # Only messages directed to the "console" user are accepted.
        if user.dest.local == "console":
            return lambda: SMTPMessage()
        raise smtp.SMTPBadRcpt(user)

class SMTPMessage:
    implements(smtp.IMessage)
    
    def __init__(self):
        self.lines = []
    
    def lineReceived(self, line):
        self.lines.append(line)
    
    def eomReceived(self):
        print "New message received:"
        print "\n".join(self.lines)
        self.lines = None
        return defer.succeed(None)
   
    def connectionLost(self):
        # There was an error, throw away the stored lines
        self.lines = None

class SMTPFactory(smtp.SMTPFactory):
    protocol = smtp.ESMTP

    def __init__(self, *a, **kw):
        smtp.SMTPFactory.__init__(self, *a, **kw)
        self.delivery = SMTPMessageDelivery()

    def buildProtocol(self, addr):
        p = smtp.SMTPFactory.buildProtocol(self, addr)
        p.delivery = self.delivery
        p.challengers = {"LOGIN": LOGINCredentials, "PLAIN": PLAINCredentials}
        return p

class SMTPRealm:
    implements(IRealm)

    def requestAvatar(self, avatarId, mind, *interfaces):
        if smtp.IMessageDelivery in interfaces:
            return smtp.IMessageDelivery, SMTPMessageDelivery(), lambda: None
        raise NotImplementedError()
