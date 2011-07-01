from twisted.python import log
from twisted.web import resource
from twisted.words.xish import domish
from wokkel.subprotocols import XMPPHandler
from wokkel.xmppim import AvailablePresence, Presence

import simplejson as json

MAX_COMMITS = 10
NS_MUC = 'http://jabber.org/protocol/muc'
NS_XHTML_IM = 'http://jabber.org/protocols/xhtml-im'
NS_XHTML_W3C = 'http://www.w3.org/1999/xhtml'

class CommitBot(XMPPHandler):

    def __init__(self, room, nick, password=None):
        XMPPHandler.__init__(self)

        self.room = room
        self.nick = nick
        self.password = password

    def connectionMade(self):
        self.send(AvailablePresence())

        # add handlers

        # join room
        pres = Presence()
        pres['to'] = self.room + '/' + self.nick
        x = pres.addElement((NS_MUC, 'x'))
        if not self.password is None:
            x.addElement('password', content = self.password)
        self.send(pres)

    def notify(self, data):
        # build the messages
        text = []
        html = []
        link = r"<a href='%s' name='%s'>%s</a>"
        
        try:
            ltxt = link % (data['changeset_url'], data['revision'], data['revision'])
            html.append("New commits by %s:<br />%s | %s<br />" %
                        (data['author'],
                         data['message'],
                         ltxt))
                        
            html.append("Changed files:<br />")
            i = 0
            for c in data['changed_files']:
                i += 1
                html.append('%s | %s<br />' % (c[0], c[1]))
                if i == MAX_COMMITS:
                    html.append("<br />Too many commits, truncated. Showing %s of %s commits" % (i, len(data['commits'])))
                    break
                
        except:
            html.append("New commits in <a href='%s'>%s</a>:<br/>" %
                        (data['repository']['url'],
                         data['repository']['name']))
            i = 0
            for c in data['commits']:
                i += 1
                text.append('%s | %s | %s\n' % (c['message'],
                                                c['author']['email'], 
                                                c['url']))
                ltxt = link % (c['url'], c['id'], c['id'][:7])
                html.append('%s | %s | %s<br />' % (c['message'],
                                                    c['author']['email'],
                                                    ltxt))
                if i == MAX_COMMITS:
                    html.append("<br />Too many commits, truncated. Showing %s of %s commits" % (i, len(data['commits'])))
                    break

        msg = domish.Element((None, 'message'))
        msg['to'] = self.room
        msg['type'] = 'groupchat'
        msg.addElement('body', content=''.join(text))
        wrap = msg.addElement((NS_XHTML_IM, 'html'))
        body = wrap.addElement((NS_XHTML_W3C, 'body'))
        body.addRawXml(''.join(html))

        self.send(msg)


class WebHook(resource.Resource):
    isLeaf = True

    def __init__(self, bot):
        resource.Resource.__init__(self)
        self.bot = bot

    def render_GET(self, req):
        return "commitbot ready to rock!"

    def render_POST(self, req):
	try:
		data = json.loads(req.args['commit'][0])
	except:
		data = json.loads(req.args['payload'][0])
        self.bot.notify(data)
        return ""
