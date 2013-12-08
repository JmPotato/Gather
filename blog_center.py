#coding=utf-8

import sys
import os
import logging
import threading
import time
import random
from HTMLParser import HTMLParser
import feedparser
#Note: The HTMLParser module has been renamed to html.parser in Python 3.

import init_db

db = init_db.db
settings = vars(__import__("settings"))


class FeedSummaryHTMLFilter(HTMLParser):
    def __init__(self):
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
        HTMLParser.__init__(self)

    def handle_starttag(self, tag, attrs, ending=">"):
        if tag in self.handle_tags:
            self.HTML += "<%(tag)s" % vars()

            if attrs:
                for attr_key, attr_value in attrs:
                    self.HTML += ' %(attr_key)s="%(attr_value)s"' % vars()

            self.HTML += ending
            self.HTML += os.linesep

    def handle_endtag(self, tag):
        if tag in self.handle_tags:
            self.HTML += "</%(tag)s>" % vars()
            self.HTML += os.linesep

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs, ending="/>")

    def handle_data(self, data):
        self.HTML += data
        self.HTML += os.linesep
        self.TEXT += data
        self.TEXT += os.linesep

    def get_result(self, what='both'):
        # what = what.strip().lower()
        if what == 'both':
            return (self.HTML, self.TEXT)
        elif what == 'html':
            return self.HTML
        elif what == 'text':
            return self.TEXT


class FeedSyncThread(threading.Thread):
    def __init__(self, user):
        super(FeedSyncThread, self).__init__()
        self.user = user

    def run(self):
        feed = self.user.get('feed')
        role = True if self.user.get('role') >= 2 else False
        if feed and role:
            parser = feedparser.parse(feed)
            for entry in parser.get('entries'):
                title = entry.get('title') or parser['feed'].get('title') or \
                    'An Article Created by %s' % self.user['name']
                link = entry.get('links')[0].get('href') or feed.get('href')
                summary = entry.get('summary') or entry.get('value')
                _parser = FeedSummaryHTMLFilter()
                _parser.feed(summary)
                summary_html = summary_text = 'Original Page Link:' \
                    '<a href="%(link)s"> %(link)s</a>' % vars()
                summary_html += '<br/>' * 2
                summary_text += os.linesep * 2
                summary_html += _parser.get_result('html')
                summary_text += _parser.get_result('text')
                del summary
                date = entry.get('published_parsed') or \
                    entry.get('updated_parsed')
                date = time.mktime(date)

                last_time = self.user.get('feed_last_updated', 0)

                if date > last_time:
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
                    db.members.update({'_id': self.user['_id']}, {
                        '$set': {'feed_last_updated': date}})

        sys.stdout.write('%s exited.\n' % self.getName())


class FeedSyncHandler(object):
    def __init__(self):
        sys.stdout.write('Now begin.\n')
        for user in db.members.find():
            syncThread = FeedSyncThread(user=user)
            sys.stdout.write('%s for user %s...\n' % (syncThread.getName(),
                user['name_lower']))
            syncThread.start()
            time.sleep(random.random())  # cooldown

syncHandler = FeedSyncHandler()
