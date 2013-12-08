#coding=utf-8

import os
import threading
import time
import random
from HTMLParser import HTMLParser
import feedparser
#Note: The HTMLParser module has been renamed to html.parser in Python 3.

import init_db

db = init_db.db
settings = vars(__import__("settings"))
mutex = threading.Lock()


def _print(message, self=None):
    while not mutex.acquire(False):  # Do not block if unable to acquire.
        time.sleep(random.random())

    if not self:
        print message
    else:
        print '[%s] %s' % (self.getName(), message)

    mutex.release()


class FeedSummaryHTMLFilter(HTMLParser, object):
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
        super(FeedSummaryHTMLFilter, self).__init__()

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
        is_admin = True if self.user['role'] >= 2 else False
        if feed and is_admin:
            parser = feedparser.parse(feed)
            for entry in parser.get('entries')[::-1]:
                title = entry.get('title') or parser['feed'].get('title') or \
                    'An Article Created by %s' % self.user['name']
                link = entry.get('links')[0].get('href') or \
                    parser['feed'].get('href')
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

                last_time = db.members.find_one(
                    {'_id': self.user['_id']}).get('feed_last_updated', 0)

                if date > last_time:
                    _print('Creating new article: %s' % title, self)
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
                    _print('Created article successfully. ' \
                        'feed_last_updated = %s' % date, self)
                    db.members.update({'name': self.user['name']},
                        {'$set': {'feed_last_updated': date}})

        _print('%s exited.' % self.getName())


class FeedSyncHandler(object):
    def __init__(self):
        for user in db.members.find():
            syncThread = FeedSyncThread(user=user)
            _print('%s for user %s...' % (syncThread.getName(),
                user['name_lower']))
            syncThread.start()
            while int(syncThread.getName()[-1]) > 5:
                time.sleep(random.random())  # cooldown

_print('Now begin.')

command = __import__('sys').argv[1:]

if 'clear' in command or '-c' in command or '--clear' in command:
    for user in db.members.find():
        db.members.update({'_id': user['_id']},
            {"$set": {'feed_last_updated': 0}})
        _print('Clean feed_last_updated for user %s successfully.' % user['name'])
else:
    syncHandler = FeedSyncHandler()
