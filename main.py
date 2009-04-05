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
import re
from datetime import datetime

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
    selfDict['id'] = str(self.key())
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
  def get(self):
    items_query = CommunityItem.all().order('-creation_date')
    items = items_query.fetch(10)

    if users.get_current_user():
      url = users.create_logout_url(self.request.uri)
      url_linktext = 'Logout'
    else:
      url = users.create_login_url(self.request.uri)
      url_linktext = 'Login'
      
    content_type = self.get_content_type_from_url()
      
    if content_type == 'plist':
      #self.response.out.write('<ul>\n')
      #for item in items:
        #self.response.out.write('<li>%s</li>\n' % item)
      #self.response.out.write('</ul>\n')
      plist = plistlib.writePlistToString(items)
      self.response.out.write(plist)
    elif content_type == 'xml':
      pass
      # TODO: send back Atom
    elif content_type == 'html':
      pass
      # TODO: send back templated html
    
  def post(self):
    communityItem = CommunityItem()
    self.add(communityItem)
    self.redirect('/community/')

  def add(self,communityItem):
    if users.get_current_user():
      communityItem.creator = users.get_current_user()

    communityItem.content = self.request.get('content')
    communityItem.creation_date = datetime.now()
    communityItem.put()
    
  def get_content_type_from_url(self):
    url = self.request.path_info
    ctype_regexp = re.compile(r'.*/items\.([^\.]+)')
    matches = ctype_regexp.match(url)
    content_type = matches.group(1)
    return content_type
    
  def get_id_from_url(self):
    url = self.request.path_info
    id_regexp = re.compile(r'.*/(?:item|event|chatter)/([^/]+)')
    matches = id_regexp.match(url)
    the_id = matches.group(1)
    return the_id
    
  def delete(self):
    delete_id = self.get_id_from_url()
    #self.response.out.write('Deleting item %s' % deleteId)
    item = db.get(delete_id)
    item.delete()
    
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
    path = os.path.join(os.path.dirname(__file__), 'test.html')
    self.response.out.write(template.render(path, template_values))
    
class EventHandler(CommunityItemHandler):
  def post(self):
    event = Event()
    event.date = datetime.strptime(self.request.get('date'),'%Y-%m-%d %H-%M-%S')
    event.location = self.request.get('location')
    self.add(event)
    
class ChatterHandler(CommunityItemHandler):
  def post(self):
    chatter = Chatter()
    chatter.parent_item = db.get(self.request.get('parent_item'))
    self.add(chatter)
    
class CommentHandler(CommunityItemHandler):
  def post(self):
    parent_id = self.get_id_from_url()
    comment = Comment()
    comment.parent_item = db.get(parent_id)
    self.add(comment)

def main():
  application = webapp.WSGIApplication([('/community/', CommunityItemHandler),
                                        (r'/community/items\.[^\.]+',CommunityItemHandler),
                                        ('/community/test', TestHandler),
                                        ('/community/item/.*', CommunityItemHandler),
                                        ('/community/event/.*', EventHandler),
                                        ('/community/chatter/.*', ChatterHandler),
                                        ('/community/item/[^/]+/comment', CommentHandler),
                                       ],
                                         debug=True)
  run_wsgi_app(application)


if __name__ == '__main__':
  main()
