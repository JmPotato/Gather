# -*- coding:utf-8 -*-

from flask import Blueprint, render_template, make_response
from gather.notification.models import Notification

bp = Blueprint("notification", __name__, url_prefix="/notification")


@bp.route("/", defaults={'page':1})
@bp.route("/page/<int:page>")
def index():
    notifications = Notification.query.order_by(Notification.updated.desc()).paginate(page)
    return render_template("notification/index.html", notifications=notifications)
