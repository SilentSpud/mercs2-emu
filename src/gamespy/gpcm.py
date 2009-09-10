import logging

from twisted.internet.protocol import ServerFactory

from login import LoginServer
from message import MessageFactory
import db
import cipher

# i'm prettuy sure gpcm stands for GamesPy CoMrade

class Comrade(LoginServer):
   def recv_login(self, msg):
      # receive this:
      # \login\
      # \challenge\mDDSIHggE7HnWgcZhojg0CUsTVyDw4fV
      # \authtoken\CCUBnHUPERml+OVgejfpuXqQS9VmzKBnBalrwEnQ8HBNvxOl/8qpukAzGCJ1HzTundOT8w6gFXNtNk4bDJnd0xtgw== # encoded using server challenge sent via ea login
      # \partnerid\0
      # \response\553d5fa1918fc0716d5f11f4475878af
      # \firewall\1
      # \port\0
      # \productid\11419
      # \gamename\redalert3pc
      # \namespaceid\1
      # \sdkrevision\11
      # \quiet\0
      # \id\1
      # \final\

      # TODO: extract info from authtoken, once i can decode it
      # for now, find user by ip

      self.user = user = db.LoginSession.objects.get(extIp=self.transport.getPeer().host).user # HACK
      persona = user.getPersona()

      #persona = db.Persona(name='Jackalus', user=user)
      #print ('proof', user.password, persona.name, msg.map['challenge'], self.sChal)
      blk = [] ## dunno what this is
      self.sendMsg(MessageFactory.getMessage([('blk', len(blk)), ('list', ','.join(blk))]))

      ## send buddy list
      buddies = [str(x.id) for x in persona.friends.all()]
      self.sendMsg(MessageFactory.getMessage([('bdy', len(buddies)), ('list', ','.join(buddies))]))

      ## TODO: login ticket and session key should change every login
      lt = 'XdR2LlH69XYzk3KCPYDkTY__'
      sessKey = '171717' ## HACK, FIXME
      self.sendMsg(MessageFactory.getMessage([
         ('lc', '2'),
         ('sesskey', sessKey),
         ## differs from regular gs login proof in that chall and ticket send to user are used instead of pwd, username
         ('proof', cipher.gs_login_proof(user.loginsession.key, msg.map['authtoken'], msg.map['challenge'], self.sChal)),
         ('userid', user.id),
         ('profileid', persona.id),
         ('uniquenick', persona.name),         ('lt', lt),
         ('id', '1')
      ]))

      #HACKy way to maintain a list of all client connections
      if not hasattr(self.factory, 'conns'):
         self.factory.conns = {}
      self.factory.conns[self.user] = self

   def recv_pinvite(self, msg):
      ## \pinvite\\sesskey\18500069\profileid\165580977\productid\11419\location\1 959918388 0 PW: #HOST:Keb Keb #FROM:Keb #CHAN:#GSP!redalert3pc!MPlPcDD4PM\final\
      loc = msg.map['location']
      tokens = loc.split(' ')
      ## guesses on location tokens:
      ## chan id the inviter is in, hoster?, gamename?, fromwho, gamechan inviting to
      who = msg.map['profileid']
      ## HACK: race condition here too (if client disconnects as we're sending)
      #  \ka\\final\
      try:
         persona = db.Persona.objects.get(id=who)
         ## TODO: RE all the other bm/10* status msgs. there are a lot, grep the logs
         self.factory.conns[persona.user].sendMsg(MessageFactory.getMessage([
            ('bm', 101),
            ('f', persona.id), ## f = from?
            ('msg', '|'.join(['', 'p', msg.map['productid'], 'l', ' '.join(tokens)])),
         ]))
      except db.Persona.DoesNotExist, ex: ## TODO, FIXME: sometimes (always firsttime for coop invite)I get weird ids, including the BE int of my old publicip?? where are these vals coming from
         ## and what is the proper way to handle them??
         print 'couldnt lookup profile id:', who
         print 'heres full msg:', msg



class ComradeFactory(ServerFactory):
   protocol =  Comrade
   log = logging.getLogger('gamespy.gpcm')

