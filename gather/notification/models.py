# -*- coding:utf-8 -*-

from __future__ import unicode_literals

from gather.extensions import db, cache


class Notification(db.Model):
    author = db.relationship(Reply)
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