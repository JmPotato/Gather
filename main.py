#!/usr/bin/env python
#coding=utf-8

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import pymongo
from tornado.options import define, options
import os

define('port', default=8888, help='run on the given port', type=int)
define('mongo_host', default='127.0.0.1', help='mongodb host')
define('mongo_port', default=27017, help='mongodb port')
define('memcached_host', default=['127.0.0.1'],help='memcached host')

from auth import AuthSignupHandler,AuthLoginHandler,AuthLogoutHandler,AuthInfoHandler,AuthSettingHandler,AuthChangePasswordHandler,NotificationHandler,BlockUserHandler
from post import PostHandler,PostViewHandler,MarkDownPreViewHandler,PostListModule,TopicsViewHandler,MarkPostHandler,MyMarkedPostHandler
from tag import TagViewHandler,TagCloudHandler,TagFeedHandler,TagCloudModule
from admin import RemoveUserHandler,RemovePostHandler,RemoveCommentHandler,ChangeTagHandler
from t import TwitterOauthHandler,TwitterNotBindHandler,TweetHandler
from g import ImgurOauthHandler,ImgurUploadHandler,ImgurUnbindHandler
from common import HomeHandler,FeedHandler,EditModule,ErrorHandler
from config import config,consumer_key,consumer_secret,database_name
from pwd import GetPwdHandler,ResetPwdHandler
import pylibmc

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/', HomeHandler),
            (r'/feed', FeedHandler),

            (r'/signup', AuthSignupHandler),
            (r'/login', AuthLoginHandler),
            (r'/logout', AuthLogoutHandler),
            (r'/user/([A-Za-z0-9]+)',AuthInfoHandler),
            (r'/user/([A-Za-z0-9]+)/block',BlockUserHandler),
            (r'/setting',AuthSettingHandler),
            (r'/setting/password',AuthChangePasswordHandler),
            (r'/setting/getpwd',GetPwdHandler),
            (r'/setting/resetpwd/(\w{32})',ResetPwdHandler),

            (r'/my/post',MyMarkedPostHandler),
            (r'/my/notifications',NotificationHandler),

            (r'/topics',TopicsViewHandler),
            (r'/topics/(\d+)', PostViewHandler),
            (r'/topics/(\d+)/mark',MarkPostHandler),
            (r'/topics/add', PostHandler),

            (r'/tag', TagCloudHandler),
            (r'/tag/(.+)', TagViewHandler),
            (r'/feed/(.+)', TagFeedHandler),

            (r'/admin/user/kill/(.*?)',RemoveUserHandler),
            (r'/admin/post/kill/(\d+)',RemovePostHandler),
            (r'/admin/post/kill/(\d+)/(\d+)',RemoveCommentHandler),
            (r'/admin/post/changetag/(\d+)',ChangeTagHandler),

            (r'/twitter/oauth',TwitterOauthHandler),
            (r'/twitter/unbind',TwitterNotBindHandler),
            (r'/twitter/tweet',TweetHandler),

            (r'/imgur/oauth',ImgurOauthHandler),
            (r'/imgur/unbind',ImgurUnbindHandler),
            (r'/imgur/upload',ImgurUploadHandler),

            (r'/markdown',MarkDownPreViewHandler),

            (r'.*',ErrorHandler),

        ]

        settings = dict(
            ui_modules={"Post": PostListModule,
                        "TagCloud": TagCloudModule,
                        "Edit":EditModule},
            autoescape=None,
            login_url='/login',
            template_path=os.path.join(os.path.dirname(__file__), 'templates'),
            static_path=os.path.join(os.path.dirname(__file__), 'static'),
            gzip=True,
            **config
        )

        tornado.web.Application.__init__(self, handlers, **settings)

        self.db = pymongo.Connection(host=options.mongo_host,port=options.mongo_port)[database_name]

        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret

        self.mc = pylibmc.Client(options.memcached_host,binary=True)
        
        if not self.db.settings.find_one({'post_id':{'$lte':0}}):
            self.db.settings.save({'post_id':1})
            self.db.settings.save({'user_id':0})
            self.db.posts.create_index([('changedtime',1)])

if __name__ == '__main__':
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()