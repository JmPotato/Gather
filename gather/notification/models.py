# -*- coding:utf-8 -*-

from __future__ import unicode_literals

from gather.extensions import db, cache
from gather.account.models import Account
from gather.topic.models import Topics

class Notification(db.Model):
    author = db.relationship(Account)
    topic = db.relationship(Topic)
    created = db.Column(
        db.Datetime,
        db.ForeignKey('reply.created'), index=True
    )
    changed = db.Column(
        db.Datetime,
        db.ForeignKey('reply.changed'), nullable=True
    )
    content = db.Column(
        db.Text(),
        db.ForeignKey('Reply.content')
    )
    floor = db.Column(db.Integer, nullable=False)