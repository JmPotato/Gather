# coding=utf-8

import time
import logging
import tornado.web

from . import BaseHandler
from bson.objectid import ObjectId
from .utils import make_content


class TopicListHandler(BaseHandler):
    def get(self):
        topics = self.db.topics.find(sort=[('last_reply_time', -1)])
        topics_count = topics.count()
        p = int(self.get_argument('p', 1))
        self.render(
            'topic/list.html', topics=topics,
            topics_count=topics_count, p=p
        )


class TopicHandler(BaseHandler):
    def get(self, topic_id):
        topic = self.get_topic(topic_id)
        if self.current_user:
            self.db.notifications.update({
                'topic': ObjectId(topic_id),
                'to': self.current_user['name_lower']
            }, {'$set': {'read': True}}, multi=True)
            if 'read' in topic:
                self.db.topics.update(
                    {'_id': ObjectId(topic_id)},
                    {'$addToSet': {'read': self.current_user['name_lower']}}
                )
            else:
                self.db.topics.update(
                    {'_id': ObjectId(topic_id)},
                    {'$set': {'read': [self.current_user['name_lower']]}}
                )
        replies = self.db.replies.find({'topic': topic_id},
                                       sort=[('index', 1)])
        replies_count = replies.count()
        p = int(self.get_argument('p', 1))
        if p < 1:
            p = 1

        self.render('topic/topic.html', topic=topic,
                    replies=replies, replies_count=replies_count,
                    p=p)


class CreateHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        node_name = self.get_argument("node", "")
        self.render('topic/create.html', node_name=node_name)

    @tornado.web.authenticated
    def post(self):
        node = self.get_argument("node", '')
        title = self.get_argument('title', '')
        content = self.get_argument('content', '')
        if not (node and title and content):
            self.flash('Please fill the required field')
        if len(title) > 100:
            self.flash("The title is too long")
        if len(content) > 20000:
            self.flash("The content is too long")
        if not self.get_node(node):
            raise tornado.web.HTTPError(403)
        if self.messages:
            self.render('topic/create.html', node_name=node)
            return
        topic = self.db.topics.find_one({
            'title': title,
            'content': content,
            'author': self.current_user['name']
        })
        if topic:
            self.redirect('/topic/%s' % topic['_id'])
            return
        time_now = time.time()
        content_html = make_content(content)
        data = {
            'title': title,
            'content': content,
            'content_html': content_html,
            'author': self.current_user['name'],
            'node': node,
            'created': time_now,
            'modified': time_now,
            'last_reply_time': time_now,
            'index': 0,
        }
        source = self.get_source()
        if source:
            data['source'] = source
        topic_id = self.db.topics.insert(data)
        self.send_notification(content_html, topic_id)
        self.redirect('/topic/%s' % topic_id)


class ReplyHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self, topic_id):
        content = self.get_argument('content', None)
        if not content:
            self.flash('Please fill the required field')
        elif len(content) > 20000:
            self.flash("The content is too long")
        if self.messages:
            self.redirect('/topic/%s' % topic_id)
            return
        reply = self.db.replies.find_one({
            'topic': topic_id,
            'content': content,
            'author': self.current_user['name']
        })
        if reply:
            self.redirect('/topic/%s' % topic_id)
            return
        index = self.db.topics.find_and_modify({'_id': ObjectId(topic_id)},
                                               update={'$inc': {'index': 1}})['index'] + 1
        time_now = time.time()
        content_html = make_content(content)
        self.send_notification(content_html, topic_id)
        source = self.get_source()
        data = {
            'content': content,
            'content_html': content_html,
            'author': self.current_user['name'],
            'topic': topic_id,
            'created': time_now,
            'modified': time_now,
            'index': index,
        }
        if source:
            data['source'] = source
        self.db.replies.insert(data)
        self.db.topics.update({'_id': ObjectId(topic_id)},
                              {'$set': {'last_reply_time': time_now,
                                        'last_reply_by':
                                        self.current_user['name'],
                                        'read': [self.current_user['name_lower']]}})
        reply_nums = self.db.replies.find({'topic': topic_id}).count()
        last_page = self.get_page_num(reply_nums,
                                      self.settings['replies_per_page'])
        self.redirect('/topic/%s?p=%s' % (topic_id, last_page))


class RemoveHandler(BaseHandler):
    def post(self, topic_id):
        self.check_role(owner_name=self.current_user['name'])
        topic_id = ObjectId(topic_id)
        topic = self.get_topic(topic_id)
        self.captureMessage(
            "%s removed a topic" % self.current_user["name"],
            data={
                "level": logging.INFO
            },
            extra={
                "topic": topic
            }
        )
        self.db.histories.remove({"target_id": topic_id})
        self.db.topics.remove({'_id': topic_id})
        self.db.replies.remove({'topic': topic_id})
        self.db.notifications.remove({'topic': ObjectId(topic_id)})
        self.flash('Removed successfully', type='success')


class EditHandler(BaseHandler):
    def get(self, topic_id):
        topic = self.get_topic(topic_id)
        self.check_role(owner_name=topic['author'])
        node = self.get_node(topic['node'])
        self.render('topic/edit.html', topic=topic,
                    node=node)

    def post(self, topic_id):
        topic = self.get_topic(topic_id)
        self.check_role(owner_name=topic['author'])
        title = self.get_argument('title', '')
        content = self.get_argument('content', '')
        if not (title and content):
            self.flash('Please fill the required field')
        if len(title) > 100:
            self.flash("The title is too long")
        if len(content) > 20000:
            self.flash("The content is too long")
        if self.messages:
            self.render('topic/edit.html', topic=topic)
            return
        if content == topic['content'] and title == topic['title']:
            self.redirect('/topic/%s' % topic_id)
            return
        if title != topic['title']:
            self.save_history(topic_id, topic['title'], title, type="title")
            topic['title'] = title
        if content != topic['content']:
            self.save_history(topic_id, topic['content'], content)
            topic['content'] = content
            content = make_content(content)
            self.db.notifications.update({'content': topic['content_html'],
                                          'topic': ObjectId(topic_id)},
                                         {'$set': {'content': content}})
            topic['content_html'] = content
        topic['modified'] = time.time()
        self.db.topics.save(topic)
        self.flash('Saved successfully', type='success')
        self.redirect('/topic/%s' % topic_id)


class MoveHandler(BaseHandler):
    def get(self, topic_id):
        topic = self.get_topic(topic_id)
        self.render('topic/move.html', topic=topic)

    def post(self, topic_id):
        node_name = self.get_argument('node', '')
        import logging
        logging.info(node_name)
        node = self.get_node(node_name.lower())
        self.db.topics.update({'_id': ObjectId(topic_id)},
                              {'$set': {'node': node['name']}})
        self.flash('Moved successfully', type='success')
        self.redirect('/topic/%s' % topic_id)


class EditReplyHandler(BaseHandler):
    def get(self, reply_id):
        reply = self.db.replies.find_one({'_id': ObjectId(reply_id)})
        if not reply:
            raise tornado.web.HTTPError(404)
        self.check_role(owner_name=reply['author'])
        self.render('topic/edit_reply.html', reply=reply)

    def post(self, reply_id):
        reply = self.db.replies.find_one({'_id': ObjectId(reply_id)})
        if not reply:
            raise tornado.web.HTTPError(404)
        self.check_role(owner_name=reply['author'])
        content = self.get_argument('content', '')
        if not content:
            self.flash('Please fill the required field')
        elif len(content) > 20000:
            self.flash("The content is too long")
        if self.messages:
            self.render('topic/edit_reply.html', reply=reply)
            return
        if content == reply['content']:
            self.redirect(self.get_argument('next', '/'))
            return
        self.save_history(reply_id, reply['content'], content)
        reply['modified'] = time.time()
        reply['content'] = content
        content = make_content(content)
        self.db.notifications.update({'content': reply['content_html']},
                                     {'$set': {'content': content}})
        reply['content_html'] = content
        self.db.replies.save(reply)
        self.flash('Saved successfully', type='success')
        self.redirect(self.get_argument('next', '/'))


class RemoveReplyHandler(BaseHandler):
    def post(self, reply_id):
        self.check_role(owner_name=self.current_user['name'])
        reply_id = ObjectId(reply_id)
        reply = self.db.replies.find_one({'_id': reply_id})
        if not reply:
            raise tornado.web.HTTPError(404)
        self.db.notifications.remove({
            'from': reply['author'].lower(),
            'content': reply['content_html'],
        }, multi=True)
        topic = self.get_topic(reply['topic'])
        self.captureMessage(
            "%s removed a reply" % self.current_user["name"],
            data={
                "level": logging.INFO
            },
            extra={
                "reply": reply,
                "topic": topic
            }
        )
        self.db.histories.remove({"target_id": reply_id})
        self.db.replies.remove({'_id': reply_id})
        self.flash('Removed successfully', type='success')


class HistoryHandler(BaseHandler):
    def get(self, id):
        self.check_role(role_min=5)
        id = ObjectId(id)
        histories = self.db.histories.find(
            {"target_id": id},
            sort=[('created', 1)]
        )
        self.render("topic/history.html", histories=histories)


class TopicList(tornado.web.UIModule):
    def render(self, topics):
        return self.render_string("topic/modules/list.html", topics=topics)


class Paginator(tornado.web.UIModule):
    def render(self, p, perpage, count, base_url):
        return self.render_string("topic/modules/paginator.html", p=p,
                                  perpage=perpage, count=count, base_url=base_url)


handlers = [
    (r'/', TopicListHandler),
    (r'/topic', TopicListHandler),
    (r'/topic/create', CreateHandler),
    (r'/topic/(\w+)', TopicHandler),
    (r'/topic/(\w+)/edit', EditHandler),
    (r'/topic/(\w+)/reply', ReplyHandler),
    (r'/topic/(\w+)/remove', RemoveHandler),
    (r'/topic/(\w+)/move', MoveHandler),
    (r'/reply/(\w+)/edit', EditReplyHandler),
    (r'/reply/(\w+)/remove', RemoveReplyHandler),
    (r'/history/(\w+)/', HistoryHandler)
]

ui_modules = {
    'topic_list': TopicList,
    'paginator': Paginator,
}
