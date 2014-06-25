# -*- coding:utf-8 -*-

import re
import bleach
import datetime

from flask import url_for, g
from flask.ext.sqlalchemy import models_committed
from markupsafe import Markup
from tornado.escape import xhtml_escape, to_unicode, _URL_RE
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, TextLexer
from gather.account.models import Account
from gather.node.models import Node
from gather.topic.models import Topic, Reply
from gather.extensions import cache
from gather.utils import gen_action_token


_CODE_RE = re.compile(r'```(\w+)(.+?)```', re.S)
_MENTION_RE = re.compile(r'((?:^|\W)@\w+)')
_FLOOR_RE = re.compile(r'((?:^|[^&])#\d+)')
_EMAIL_RE = re.compile(r'([A-Za-z0-9-+.]+@[A-Za-z0-9-.]+)(\s|$)')
formatter = HtmlFormatter()


def get_site_status():
    account, node, topic, reply = cache.get_many(
        'status-account', 'status-node', 'status-topic', 'status-reply'
    )
    if not account:
        account = Account.query.count()
        cache.set('status-account', account)
    if not node:
        node = Node.query.count()
        cache.set('status-node', node)
    if not topic:
        topic = Topic.query.count()
        cache.set('status-topic', topic)
    if not reply:
        reply = Reply.query.count()
        cache.set('status-reply', reply)
    return dict(
        account=account,
        node=node,
        topic=topic,
        reply=reply,
    )


def _clear_cache(sender, changes):
    for model, operation in changes:
        if isinstance(model, Account) and operation != 'update':
            cache.delete('status-account')
        if isinstance(model, Node) and operation != 'update':
            cache.delete('status-node')
        if isinstance(model, Topic) and operation != 'update':
            cache.delete('status-topic')
        if isinstance(model, Reply) and operation != 'update':
            cache.delete('status-reply')


models_committed.connect(_clear_cache)


def sanitize(content):
    return bleach.linkify(content)


@cache.memoize(timeout=3600*24)
def content_to_html(text, extra_params='rel="nofollow"'):
    if not text.strip():
        return ""
    if extra_params:
        extra_params = " " + extra_params.strip()

    def make_link(m):
        url = m.group(1)
        proto = m.group(2)

        href = m.group(1)
        if not proto:
            href = "http://" + href   # no proto specified, use http

        params = extra_params

        if '.' in href:
            name_extension = href.split('.')[-1].lower()
            if name_extension in ('jpg', 'png', 'gif', 'jpeg'):
                return u'<img src="%s" />' % href

        return u'<a href="%s"%s>%s</a>' % (href, params, url)

    def cover_email(m):
        data = {'mail': m.group(1),
                'end': m.group(2)}
        return u'<a href="mailto:%(mail)s">%(mail)s</a>%(end)s' % data

    def convert_mention(m):
        data = {}
        data['begin'], data['user'] = m.group(1).split('@')
        data["user_profile"] = url_for("user.profile", name=data['user'])
        t = u'%(begin)s<a href="%(user_profile)s" class="mention_user">' \
            u'@%(user)s</a>'
        return t % data

    def convert_floor(m):
        data = {}
        data['begin'], data['floor'] = m.group(1).split('#')
        t = u'%(begin)s<a href="#reply_%(floor)s" ' \
            u'class="mention_floor">#%(floor)s</a>'
        return t % data

    def highligt(m):
        try:
            name = m.group(1)
            lexer = get_lexer_by_name(name)
        except ValueError:
            lexer = TextLexer()
        text = m.group(2).replace('&quot;', '"').replace('&amp;', '&')
        text = text.replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&nbsp;', ' ')
        return highlight(text, lexer, formatter)

    text = to_unicode(xhtml_escape(text)).replace(' ', '&nbsp;')
    text = _CODE_RE.sub(highligt, text).replace('\n', '<br />')
    text = _MENTION_RE.sub(convert_mention, text)
    text = _EMAIL_RE.sub(cover_email, text)
    text = _FLOOR_RE.sub(convert_floor, text)
    return Markup(_URL_RE.sub(make_link, text))


def xmldatetime(value):
    if not isinstance(value, datetime.datetime):
        return value
    return value.strftime('%Y-%m-%dT%H:%M:%SZ')


def url_for_other_page(page):
    from flask import request, url_for
    args = request.view_args.copy()
    args["page"] = int(page)
    return url_for(request.endpoint, **args)


def url_for_with_token(endpoint, **values):
    if not g.user:
        return
    values["token"] = gen_action_token(40)
    return url_for(endpoint, **values)
