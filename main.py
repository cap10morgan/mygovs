#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#



import cgi
import wsgiref.handlers
import os

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.ext.webapp import template

import plistlib

class CommunityItem(db.Model):
  creator = db.UserProperty()
  content = db.StringProperty(multiline=True)
  creation_date = db.DateTimeProperty(auto_now_add=True)
  display_in_list = True
  
  def __str__(self):
    #return '(' + self.creation_date.isoformat() + ') ' + self.creator + ': ' + self.content
    return self.content
    
  def serialize(self):
    selfDict = dict()
    selfDict['creator'] = self.creator
    selfDict['content'] = self.content
    selfDict['creation_date'] = str(self.creation_date)
    return selfDict

class Event(CommunityItem):
  date = db.DateTimeProperty()
  location = db.GeoPtProperty()

class Chatter(CommunityItem):
  parent_item = db.ReferenceProperty(CommunityItem)
  
class Comment(Chatter):
  display_in_list = False
  
class CommunityItemHandler(webapp.RequestHandler):
  def post(self):
    communityItem = CommunityItem()

    if users.get_current_user():
      communityItem.creator = users.get_current_user()

    communityItem.content = self.request.get('content')
    #communityItem.creation_date = 0 # TODO
    communityItem.put()
    self.redirect('/')
    
class TestHandler(webapp.RequestHandler):
  def get(self):
    if users.get_current_user():
      url = users.create_logout_url(self.request.uri)
      url_linktext = 'Logout'
    else:
      url = users.create_login_url(self.request.uri)
      url_linktext = 'Login'
    template_values = {
      'url': url,
      'url_linktext': url_linktext,
    }
    path = os.path.join(os.path.dirname(__file__), 'index.html')
    self.response.out.write(template.render(path, template_values))

class MainHandler(webapp.RequestHandler):
  def get(self):
    #self.response.out.write('<h1>Hello?</h1>')
    # should use Atom someday, but for now we'll use plists because it's
    # easier with the iPhone SDK
    #self.response.out.write('<?xml version="1.0" encoding="UTF-8"?>\n\n')
    #self.response.out.write('<feed xmlns="http://www.w3.org/2005/Atom">')
    
    # need to figure out how to get all items created after a given item
    
    items_query = CommunityItem.all().order('-creation_date')
    items = items_query.fetch(10)
    
    if users.get_current_user():
      url = users.create_logout_url(self.request.uri)
      url_linktext = 'Logout'
    else:
      url = users.create_login_url(self.request.uri)
      url_linktext = 'Login'
    
    #self.response.out.write('<ul>\n')
    #for item in items:
      #self.response.out.write('<li>%s</li>\n' % item)
    #self.response.out.write('</ul>\n')
    
    plist = plistlib.writePlistToString(items)
    self.response.out.write(plist)
      
    #template_values = {
    #  'greetings': greetings,
    #  'url': url,
    #  'url_linktext': url_linktext,
    #}
    
    #path = os.path.join(os.path.dirname(__file__), 'index.html')
    #self.response.out.write(template.render(path, template_values))
    

def main():
  application = webapp.WSGIApplication([('/', MainHandler),
                                        ('/test', TestHandler),
                                        ('/item', CommunityItemHandler),
                                        #('/event', EventHandler),
                                        #('/chatter', ChatterHandler),
                                        #('/item/*/comment', CommentHandler),
                                       ],
                                         debug=True)
  run_wsgi_app(application)


if __name__ == '__main__':
  main()
