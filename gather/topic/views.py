# -*- coding:utf-8 -*-

from flask import Blueprint
from flask import url_for, g, redirect, render_template, abort, request
from gather.utils import require_token
from gather.account.utils import require_login, require_staff, require_admin
from gather.node.models import Node
from gather.notification.utils import new_notifications
from .forms import CreateTopicForm, ChangeTopicForm, ReplyForm, ChangeReplyForm
from .models import Topic, Reply

bp = Blueprint("topic", __name__, url_prefix="/topic")


@bp.route("/", defaults={'page': 1})
@bp.route('/page/<int:page>')
def index(page):
    paginator = Topic.query.order_by(Topic.created.desc()).paginate(page)
    return render_template('topic/index.html', paginator=paginator)


@bp.route("/create", methods=("GET", "POST"))
@require_login
def create():
    form = CreateTopicForm()
    if "node" in request.args:
        try:
            nid = int(request.args.get("node"))
        except ValueError:
            pass
        else:
            form.node.data = Node.query.get_or_404(nid)
    if form.validate_on_submit():
        topic = form.create()
        new_notifications(topic, is_topic=True, topic_id=topic.id)
        return redirect(url_for(".topic", topic_id=topic.id))
    return render_template("topic/create.html", form=form)


@bp.route("/<int:topic_id>", methods=("GET", "POST"), defaults={'page': 1})
@bp.route("/<int:topic_id>/page/<int:page>", methods=("GET", "POST"))
def topic(topic_id, page):
    topic = Topic.query.get_or_404(topic_id)
    form = ReplyForm()
    if g.user and form.validate_on_submit():
        reply = form.create(topic=topic)
        new_notifications(reply, is_topic=False, topic_id=reply.topic_id)
        return redirect(url_for(".topic", topic_id=topic.id, page=topic.last_page))
    replies = Reply.query.filter_by(topic=topic).order_by(Reply.id.asc())
    paginator = replies.paginate(page)
    if g.user:
        topic.mark_read(g.user)
    return render_template(
        "topic/topic.html", topic=topic, form=form,
        paginator=paginator
    )


@bp.route("/<int:topic_id>/remove/<token>")
@require_admin
@require_token
def remove_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    topic.delete()
    return redirect("/")


@bp.route("/<int:topic_id>/change", methods=("GET", "POST"))
@require_staff
def change_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    form = ChangeTopicForm(obj=topic)
    if form.validate_on_submit():
        topic = form.save(topic=topic)
        return redirect(url_for(".topic", topic_id=topic.id))
    return render_template("topic/change.html", form=form)


@bp.route("/<int:topic_id>/<int:reply_id>/change", methods=("GET", "POST"))
@require_staff
def change_reply(topic_id, reply_id):
    topic = Topic.query.get_or_404(topic_id)
    reply = Reply.query.get_or_404(reply_id)
    if reply.topic != topic:
        abort(233)
    form = ChangeReplyForm(obj=reply)
    if form.validate_on_submit():
        form.save(reply=reply)
        return redirect(url_for(".topic", topic_id=topic.id))
    return render_template("topic/change_reply.html", form=form)
