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
from google.appengine.ext.db import polymodel
from google.appengine.ext.webapp import template

import plistlib

class CommunityItem(polymodel.PolyModel):
  creator = db.UserProperty()
  message = db.StringProperty(multiline=True)
  subject = db.StringProperty(multiline=False)
  exturl = db.StringProperty(multiline=False)
  appurl = db.StringProperty(multiline=False)
  exturl_title = db.StringProperty(multiline=False)
  appurl_title = db.StringProperty(multiline=False)
  creation_date = db.DateTimeProperty(auto_now_add=True)
  display_in_list = db.BooleanProperty(default=True)
  
  def __str__(self):
    return self.message
    
  def serialize(self):
    selfDict = dict()
    selfDict['id']            = str(self.key())
    selfDict['creator']       = str(self.creator)
    selfDict['message']       = self.message
    selfDict['subject']       = self.subject
    selfDict['exturl']        = self.exturl
    selfDict['appurl']        = self.appurl
    selfDict['exturl_title']  = self.exturl_title
    selfDict['appurl_title']  = self.appurl_title
    selfDict['creation_date'] = str(self.creation_date)
    return selfDict

class Event(CommunityItem):
  event_date    = db.DateTimeProperty()
  location      = db.GeoPtProperty()
  location_desc = db.StringProperty(multiline=False)
  # TODO: Figure out how to store these
  #attendees = db.ArrayOfGoogleAccounts()
  
  def serialize(self):
    selfDict = super(Event, self).serialize
    selfDict['event_date']    = self.event_date
    selfDict['location']      = self.location
    selfDict['location_desc'] = self.location_desc
    return selfDict
    

class Chatter(CommunityItem):
  pass
  
class Comment(Chatter):
  # this doesn't work, but I'd like to set it here
  #self.display_in_list = False
  pass
  
class CommunityItemHandler(webapp.RequestHandler):
  def get_item(self,item):
    if item == None:
      return None
    continue_url = self.request.get('continue_url')
    if users.get_current_user():
      google_url = users.create_logout_url(self.request.uri)
      google_url_linktext = 'Logout'
    else:
      if continue_url:
        google_url = users.create_login_url(continue_url)
      else:
        google_url = users.create_login_url(self.request.uri)
      google_url_linktext = 'Login'
      
    content_type = self.get_content_type_from_url()
    
    if content_type == 'plist':
      google_url_data = { 'url' : google_url, 'url_linktext' : google_url_linktext }
      data = { 'item' : item, 'google_urls' : google_url_data }
      plist = plistlib.writePlistToString(data)
      self.response.out.write(plist)
    elif content_type == 'xml':
      pass
      # TODO: send back Atom
    elif content_type == 'html':
      comments = Comment.all().ancestor(item.key())
      template_values = {
        'google_url': google_url,
        'google_url_linktext': google_url_linktext,
        'continue_url' : continue_url,
        'item': item,
        'comments' : comments,
      }
      path = os.path.join(os.path.dirname(__file__), 'item.html')
      self.response.out.write(template.render(path, template_values))
  
  def get(self):
    item_id = self.get_id_from_url()
    if (item_id):
      return self.get_item(CommunityItem.get(item_id))
    
    items_offset = self.request.get('items_offset')
    if (items_offset.isdigit()):
      items_offset = int(items_offset)
    else:
      items_offset = 0
    items_limit = self.request.get('items_limit')
    if (items_limit.isdigit()):
      items_limit = int(items_limit)
    else:
      items_limit = 30
    not_older_than = self.request.get('not_older_than')
    if (not not_older_than):
      not_older_than = '2009-01-01'
    not_older_than = datetime.strptime(not_older_than,'%Y-%m-%d')
    
    items = self.retrieve_items(not_older_than,items_limit,items_offset)

    continue_url = self.request.get('continue_url')
    if users.get_current_user():
      google_url = users.create_logout_url(self.request.uri)
      google_url_linktext = 'Logout'
    else:
      if continue_url:
        google_url = users.create_login_url(continue_url)
      else:
        google_url = users.create_login_url(self.request.uri)
      google_url_linktext = 'Login'
      
    content_type = self.get_content_type_from_url()
      
    if content_type == 'plist':
      google_url_data = { 'url' : google_url, 'url_linktext' : google_url_linktext }
      data = { 'items' : items, 'google_urls' : google_url_data }
      plist = plistlib.writePlistToString(data)
      self.response.out.write(plist)
    elif content_type == 'xml':
      pass
      # TODO: send back Atom
    elif content_type == 'html':
      template_values = {
        'google_url': google_url,
        'google_url_linktext': google_url_linktext,
        'continue_url' : continue_url,
        'not_older_than' : not_older_than,
        'items': items,
      }
      path = os.path.join(os.path.dirname(__file__), 'items.html')
      self.response.out.write(template.render(path, template_values))
    
  def retrieve_items(self,not_older_than,limit = 1000,offset = 0):
    models = { 'CommunityItemHandler' : CommunityItem,
               'EventHandler'         : Event,
               'ChatterHandler'       : Chatter,
               'CommentHandler'       : Comment }
    klass = models[self.__class__.__name__]
    items_query = klass.all().filter('display_in_list =', True).filter("creation_date >=", not_older_than).order("-creation_date")
    return items_query.fetch(limit,offset)
    
  def post(self):
    if users.get_current_user():
      community_item = CommunityItem()
      self.store(community_item)
      self.redirect('/community/')
    
  def put(self):
    user = users.get_current_user()
    if user:
      item_id = self.get_id_from_url()
      if (item_id):
        community_item = CommunityItem.get_by_id(item_id)
        if (community_item):
          if (user == community_item.creator):
            self.store(community_item)
          else:
            # TODO: Throw back some kind of unauthorized error
            pass

  def store(self,community_item):
    if users.get_current_user():
      community_item.creator = users.get_current_user()

    community_item.message      = self.request.get('message')
    community_item.subject      = self.request.get('subject')
    community_item.exturl       = self.request.get('exturl')
    community_item.exturl_title = self.request.get('exturl_title')
    community_item.appurl       = self.request.get('appurl')
    community_item.appurl_title = self.request.get('appurl_title')
    
    # TODO: Should I figure out the subclasses' fields here?
    
    community_item.put()
    
  def get_content_type_from_url(self):
    url = self.request.path_info
    ctype_regexp = re.compile(r'.*/(?:items?|events?|chatter|comments?)\.([^\.]+)')
    matches = ctype_regexp.match(url)
    if matches != None:
      content_type = matches.group(1)
    else:
      content_type = 'html'
    return content_type
    
  def get_id_from_url(self):
    url = self.request.path_info
    id_regexp = re.compile(r'.*/(?:item|event|chatter)/([^/]+)')
    matches = id_regexp.match(url)
    if matches != None:
      the_id = matches.group(1)
      return the_id
    else:
      return None
    
  def delete(self):
    user = users.get_current_user()
    if user:
      delete_id = self.get_id_from_url()
      #self.response.out.write('Deleting item %s' % deleteId)
      item = db.get(delete_id)
      if user == item.creator:
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
    if users.get_current_user():
      event = Event()
      event.event_date = datetime.strptime(self.request.get('event_date'),'%Y-%m-%d %H-%M-%S')
      event.location = self.request.get('location')
      event.location_desc = self.request.get('location_desc')
      self.store(event)
    
  def get(self):
    super(EventHandler, self).get()
    
class ChatterHandler(CommunityItemHandler):
  def post(self):
    if users.get_current_user():
      parent = CommunityItem.get(self.request.get('parent_item'))
      chatter = Chatter(parent,'Chatter')
      self.store(chatter)
    
class CommentHandler(CommunityItemHandler):
  def post(self):
    if users.get_current_user():
      parent_id = self.get_id_from_url()
      parent = CommunityItem.get(parent_id)
      comment = Comment(parent)
      # should really handle this in the model class's constructor, oh well
      comment.display_in_list = False
      self.store(comment)
      self.redirect("/community/item/")
    
  def get(self):
    parent_id = self.get_id_from_url()
    parent = CommunityItem.get(parent_id)
    content_type = self.get_content_type_from_url()
    
    items = Comment.all().ancestor(parent)
    items = items.fetch(30)
    
    continue_url = self.request.get('continue_url')
    if users.get_current_user():
      google_url = users.create_logout_url(self.request.uri)
      google_url_linktext = 'Logout'
    else:
      if continue_url:
        google_url = users.create_login_url(continue_url)
      else:
        google_url = users.create_login_url(self.request.uri)
      google_url_linktext = 'Login'
    
    if content_type == 'plist':
      google_url_data = { 'url' : google_url, 'url_linktext' : google_url_linktext }
      data = { 'items' : items, 'google_urls' : google_url_data }
      plist = plistlib.writePlistToString(data)
      self.response.out.write(plist)
    elif content_type == 'xml':
      pass
      # TODO: send back Atom
    elif content_type == 'html':
      template_values = {
        'google_url': google_url,
        'google_url_linktext': google_url_linktext,
        'continue_url' : continue_url,
        #'not_older_than' : not_older_than,
        'items': items,
      }
      path = os.path.join(os.path.dirname(__file__), 'items.html')
      self.response.out.write(template.render(path, template_values))
    

def main():
  application = webapp.WSGIApplication([('/community/', CommunityItemHandler),
                                        (r'/community/items\.[^\.]+',CommunityItemHandler),
                                        ('/community/test', TestHandler),
                                        ('/community/item/[^/]+/comment(?:s?\.\w+)?', CommentHandler),
                                        ('/community/item/.*', CommunityItemHandler),
                                        ('/community/event/.*', EventHandler),
                                        ('/community/chatter/.*', ChatterHandler),
                                       ],
                                         debug=True)
  run_wsgi_app(application)


if __name__ == '__main__':
  main()
