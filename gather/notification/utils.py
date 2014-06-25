# -*- coding: utf-8 -*-


from gather.notification.models import Notification
from gather.account.models import Account
from gather.filters import _MENTION_RE


def _get_mentions(m):
    _, mentions = m.group(1).split("@")
    return mentions

def get_notification(user):
    return Notification.query().filter(Account.id == user.id).order_by(Notifiction.created.desc())

def new_notifications(data, is_topic, topic_id=0):
    floor = is_topic is True and 0 or data.id
    topic = is_topic is True and data or data.topic
    mentions = _MENTION_RE.sub(_get_mentions, data.content)
    for m in mentions:
        Notification(
            author=data.author,
            topic=topic,
            created=data.created,
            content=data.content,
            floor=floor
        ).save()