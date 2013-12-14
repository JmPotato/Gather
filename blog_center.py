#coding=utf-8

import sys
import os
import re
import time
import random
import urllib2
import feedparser
import traceback
from HTMLParser import HTMLParser
#Note: The HTMLParser module has been renamed to html.parser in Python 3.
import init_db

reload(sys)
sys.setdefaultencoding('utf-8')
#否则，一些 WordPress 网站会导致 UnicodeDecodeError。

db = init_db.db
settings = vars(__import__("settings"))


class HTMLFilter(HTMLParser, object):
    def __init__(self, find_tag=False):
        super(HTMLFilter, self).__init__()
        self.find_tag = find_tag
        self.attrs = []
        self.HTML = ''
        self.TEXT = ''
        self.handle_tags = [
            'p',
            'a',
            'br',
            'hr',
            'img',
            'b',
            'strong',
            'i',
            'em',
            'h1',
            'h2',
            'h3',
            'h4',
            'h5',
            'h6',
            'q',
            'blockquote',
        ]

    def handle_starttag(self, tag, attrs, ending=">"):
        if tag == self.find_tag:
            self.attrs += [attrs]
            return

        if tag in self.handle_tags and not self.find_tag:
            self.HTML += "<%(tag)s" % vars()

            if attrs:
                for attr_key, attr_value in attrs:
                    self.HTML += ' %(attr_key)s="%(attr_value)s"' % vars()

            self.HTML += ending
            self.HTML += os.linesep

    def handle_endtag(self, tag):
        if tag in self.handle_tags and not self.find_tag:
            self.HTML += "</%(tag)s>" % vars()
            self.HTML += os.linesep

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs, ending="/>")

    def handle_data(self, data):
        if not self.find_tag:
            self.HTML += data
            self.HTML += os.linesep
            self.TEXT += data
            self.TEXT += os.linesep

    def get_result(self, what='both'):
        # what = what.strip().lower()
        if self.find_tag:
            return self.attrs

        if what == 'both':
            return (self.HTML, self.TEXT)
        elif what == 'html':
            return self.HTML
        elif what == 'text':
            return self.TEXT


class FeedSyncFunction(object):
    def __init__(self, user):
        self.user = user

    def run(self):
        self.website = self.user.get('website')
        self.feed = ''
        _parser = HTMLFilter('link')
        is_admin = True if self.user['role'] >= 2 else False

        if self.website and is_admin:
            url = urllib2.urlopen(self.website)
            _parser.feed(url.read())

            for i in _parser.get_result():
                if ('rel', 'alternate') in i \
                    or ('type', 'application/rss+xml') in i \
                        or ('type', 'application/atom+xml') in i:
                        for j in i:
                            if j[0] == 'title' and \
                                ('comment' in j[1] or u'评论' in j[1]):
                                break  # 不处理评论 feed。
                            if j[0] == 'href':
                                if re.findall('[a-zA-z]+://[^\s]*', j[1]):
                                    self.feed = j[1]
                                else:
                                    if not j[1].startswith('/'):
                                        j[1] = '/' + j[1]
                                    if self.website.endswith('/'):
                                        self.website = self.website[:-1]
                                    self.feed = self.website + j[1]

                if self.feed:
                    break

        if self.feed:
            print 'Find out a feed address: %s' % self.feed
            parser = feedparser.parse(self.feed)
            for entry in parser.get('entries')[::-1]:
                title = entry.get('title') or parser['feed'].get('title') or \
                    'An Article Created by %s' % self.user['name']
                link = entry.get('links')[0].get('href') or \
                    parser['feed'].get('href')
                summary = entry.get('summary') or entry.get('value')
                if len(summary) < 100:
                    summary = entry.get('content')[0].get('value', summary)
                _parser = HTMLFilter()
                _parser.feed(summary)
                summary_html = summary_text = 'Original Page Link:' \
                    '<a href="%(link)s">%(link)s</a>' % {'link': link}
                summary_html += '<br/>' * 2
                summary_text += os.linesep * 2
                summary_html += _parser.get_result('html')
                summary_text += _parser.get_result('text')
                del summary
                date = entry.get('published_parsed') or \
                    entry.get('updated_parsed')
                date = time.mktime(date)

                last_time = db.members.find_one(
                    {'_id': self.user['_id']}).get('feed_last_updated', 0)

                if date > last_time:
                    print 'Creating new article: %s' % title
                    time_now = time.time()
                    node = settings['blog_center_node']
                    data = {
                        'title': title,
                        'content': summary_text,
                        'content_html': summary_html,
                        'author': self.user['name_lower'],
                        'node': node,
                        'created': time_now,
                        'modified': time_now,
                        'last_reply_time': time_now,
                        'index': 0,
                        'source': 'Feed Robot',
                    }
                    db.topics.insert(data)
                    db.members.update({'name': self.user['name']},
                        {'$set': {'feed_last_updated': date}})


class FeedSyncHandler(object):
    def __init__(self):
        for user in db.members.find():
            syncFunction = FeedSyncFunction(user=user)
            try:
                syncFunction.run()
            except:
                print traceback.print_exc()


command = sys.argv[1:]

if 'clear' in command or '-c' in command or '--clear' in command:
    for user in db.members.find():
        db.members.update({'_id': user['_id']},
            {"$set": {'feed_last_updated': 0}})
    print 'Clean feed_last_updated successfully.'
else:
    syncHandler = FeedSyncHandler()
