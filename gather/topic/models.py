# -*- coding:utf-8 -*-

from datetime import datetime
from gather.extensions import cache
from gather.account.models import Account
from gather.node.models import Node
from gather.extensions import db


class ReadTopic(db.Model):
    __table_args__ = (
        db.UniqueConstraint(
            'user_id', 'topic_id', name='uc_user_read_topic'
        ),
    )
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('account.id'), index=True)
    user = db.relationship(Account)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), index=True)
    topic = db.relationship("Topic")


class Reply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text(), nullable=True, default="")
    author_id = db.Column(
        db.Integer,
        db.ForeignKey('account.id'), nullable=False
    )
    author = db.relationship(Account)
    topic_id = db.Column(
        db.Integer,
        db.ForeignKey('topic.id'), index=True, nullable=False
    )
    topic = db.relationship("Topic")
    created = db.Column(db.DateTime, default=datetime.utcnow)
    changed = db.Column(
        db.DateTime,
        nullable=True,
        onupdate=datetime.utcnow
    )

    def to_dict(self):
        return {
            "id": self.id,
            "content": self.content,
            "author": self.author_id,
            "topic": self.topic_id,
            "created": self.created,
            "changed": self.changed
        }

    def save(self):
        if self.id:
            # Update reply
            self.changed = datetime.utcnow()
        else:
            topic = self.topic
            topic.updated = datetime.utcnow()
            topic.clear_read()
            topic.save()
        db.session.add(self)
        db.session.commit()
        return self


class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text(), nullable=True, default="")
    author_id = db.Column(
        db.Integer,
        db.ForeignKey('account.id'), index=True, nullable=False
    )
    author = db.relationship(Account)
    node_id = db.Column(
        db.Integer,
        db.ForeignKey('node.id'), index=True, nullable=False
    )
    node = db.relationship(Node)
    created = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    replies = db.relationship(
        "Reply", lazy='dynamic',
        order_by=Reply.id.asc()
    )
    updated = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    changed = db.Column(
        db.DateTime,
        nullable=True
    )

    def __str__(self):
        return self.title

    def __repr__(self):
        return '<Topic: %s>' % self.title

    @property
    def last_page(self):
        return Reply.query.filter_by(topic=self).paginate(1).pages or 1

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author_id,
            "node": self.node_id,
            "content": self.content,
            "created": self.created,
            "reply_count": self.replies.count(),
            "updated": self.updated,
            "changed": self.changed,
            "replies": [reply.to_dict() for reply in self.replies]
        }

    @property
    def read_cache_key(self):
        return "read_topic_%s" % self.id

    def have_read(self, user):
        read_list = cache.get(self.read_cache_key)
        if read_list and user.id in read_list:
            return True
        return ReadTopic.query.filter_by(topic=self, user=user).count()

    def mark_read(self, user):
        if self.have_read(user):
            return
        read_list = cache.get(self.read_cache_key)
        if read_list:
            read_list.append(user.id)
        else:
            read_list = [user.id]
        cache.set(self.read_cache_key, read_list)
        read_mark = ReadTopic(topic=self, user=user)
        db.session.add(read_mark)
        db.session.commit()

    def clear_read(self):
        cache.delete(self.read_cache_key)
        ReadTopic.query.filter_by(topic=self).delete()

    def save(self):
        db.session.add(self)
        db.session.commit()
        return self

    def delete(self):
        Reply.query.filter_by(topic=self).delete()
        self.clear_read()
        db.session.delete(self)
        db.session.commit()
        return self


class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    diff_content = db.Column(db.Text(), nullable=True, default="")
    author_id = db.Column(db.Integer, db.ForeignKey('account.id'))
    author = db.relationship(Account)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), index=True)
    topic = db.relationship(Topic)
    reply_id = db.Column(db.Integer, db.ForeignKey('reply.id'), index=True)
    reply = db.relationship(Reply)
    created = db.Column(db.DateTime, default=datetime.utcnow)

    def save(self):
        db.session.add(self)
        db.session.commit()
        return self