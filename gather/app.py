# -*- coding:utf-8 -*-

import os

BASEDIR = os.path.dirname(os.path.abspath(__file__))

from flask import Flask, g
from flask.ext.turbolinks import turbolinks
from jinja2 import MemcachedBytecodeCache
from gather.extensions import db, assets, mail, cache
from gather.settings import load_settings
from gather.account.utils import get_current_user
from gather.nitification.utils import get_notification


def create_app():
    app = Flask(
        __name__,
        static_folder=os.path.join(BASEDIR, "public", "static"),
        template_folder="templates"
    )
    load_settings(app)
    register_extensions(app)
    register_blurprints(app)
    register_hooks(app)
    register_jinja(app)
    return app


def register_extensions(app):
    db.init_app(app)
    assets.init_app(app)
    mail.init_app(app)
    turbolinks(app)
    cache.init_app(app)

    if app.debug:
        from flask_debugtoolbar import DebugToolbarExtension
        DebugToolbarExtension(app)


def register_blurprints(app):
    import gather.frontend
    import gather.account
    import gather.user
    import gather.node
    import gather.topic
    import gather.admin
    import gather.api

    app.register_blueprint(gather.frontend.bp)
    app.register_blueprint(gather.account.bp)
    app.register_blueprint(gather.user.bp)
    app.register_blueprint(gather.node.bp)
    app.register_blueprint(gather.topic.bp)
    app.register_blueprint(gather.admin.bp)
    app.register_blueprint(gather.api.bp)


def register_hooks(app):
    @app.before_request
    def load_user():
        g.user = get_current_user()
        g.user.notification = get_notification(g.user)


def register_jinja(app):
    from gather.filters import (
        sanitize, get_site_status,
        content_to_html, xmldatetime,
        url_for_other_page, url_for_with_token
    )
    @app.context_processor
    def register_context():
        return dict(
            site_status=get_site_status,
        )

    app.jinja_env.filters['sanitize'] = sanitize
    app.jinja_env.filters['content_to_html'] = content_to_html
    app.jinja_env.filters['xmldatetime'] = xmldatetime
    app.jinja_env.globals.update(
        url_for_other_page=url_for_other_page,
        url_for_with_token=url_for_with_token
    )

    app.jinja_env.bytecode_cache = MemcachedBytecodeCache(cache)

