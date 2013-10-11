import re
import requests
import settings

from tornado.escape import xhtml_escape, _unicode, _URL_RE
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, TextLexer

username_validator = re.compile(r'^[a-zA-Z0-9]+$')
email_validator = re.compile(r'^.+@[^.].*\.[a-z]{2,10}$', re.IGNORECASE)

_CODE_RE = re.compile(r'```(\w+)(.+?)```', re.S)
_MENTION_RE = re.compile(r'((?:^|\W)@\w+)')
_FLOOR_RE = re.compile(r'((?:^|\W)#\d+)')
_EMAIL_RE = re.compile(r'([A-Za-z0-9-+.]+@[A-Za-z0-9-.]+)(\s|$)')

formatter = HtmlFormatter()


def make_content(text, extra_params='rel="nofollow"'):
    """https://github.com/facebook/tornado/blob/master/tornado/escape.py#L238
    """
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
            if name_extension in ('jpg', 'png', 'git', 'jpeg'):
                return u'<img src="%s" />' % href

        return u'<a href="%s"%s>%s</a>' % (href, params, url)

    def cover_email(m):
        data = {'mail': m.group(1),
                'end': m.group(2)}
        return u'<a href="mailto:%(mail)s">%(mail)s</a>%(end)s' % data

    def convert_mention(m):
        data = {}
        data['begin'], data['user'] = m.group(1).split('@')
        t = u'%(begin)s<a href="/member/%(user)s" class="mention">' \
            u'@%(user)s</a>'
        return t % data

    def convert_floor(m):
        data = {}
        data['begin'], data['floor'] = m.group(1).split('#')
        t = u'%(begin)s<a href="#reply%(floor)s" class="mention mention_floor">' \
            u'#%(floor)s</a>'
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

    text = _unicode(xhtml_escape(text)).replace(' ', '&nbsp;')
    text = _CODE_RE.sub(highligt, text).replace('\n', '<br />')
    text = _EMAIL_RE.sub(cover_email, text)
    text = _MENTION_RE.sub(convert_mention, text)
    text = _FLOOR_RE.sub(convert_floor, text)
    return _URL_RE.sub(make_link, text)


def send_notify(user, message, url):
    if settings.pushover_token:
        return requests.post(
            "https://api.pushover.net/1/messages.json",
            data={
                "token": settings.pushover_token,
                "user": user,
                "message": message,
                "url": url
            },
            headers={
                "Content-type": "application/x-www-form-urlencoded"
            }
        ).json()
