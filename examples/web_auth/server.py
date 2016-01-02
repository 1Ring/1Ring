from twisted.web import server, resource
from twisted.internet import reactor

class Simple(resource.Resource):
    isLeaf = True
    def getChild(self, name, request):
        if name == '':
            return self
        return Resource.getChild(self, name, request)
    def render_GET(self, request):
        return "<html>Hello, world!</html>"

site = server.Site(Simple())

reactor.listenTCP(8080, site)
reactor.run()