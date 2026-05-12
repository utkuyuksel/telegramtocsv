import json
import os
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import case, func

import config
from models import Order, db
from scraper_engine import SESSION_FILE, DEAD_SESSION_FILE, load_sessions

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# --- Auth ---


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_user"):
            return redirect(url_for("admin.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if username == config.ADMIN_USERNAME and password == config.ADMIN_PASSWORD:
            session["admin_user"] = username
            session.permanent = True
            next_url = request.args.get("next") or url_for("admin.dashboard")
            return redirect(next_url)
        flash("Invalid username or password.", "error")
    return render_template("admin/login.html")


@admin_bp.route("/logout")
def logout():
    session.pop("admin_user", None)
    return redirect(url_for("admin.login"))


# --- Dashboard ---


@admin_bp.route("/")
@login_required
def dashboard():
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    def count_since(since):
        return Order.query.filter(Order.created_at >= since).count()

    def revenue_since(since):
        total = (
            db.session.query(func.sum(Order.amount))
            .filter(
                Order.created_at >= since,
                Order.tier == "paid",
                Order.payment_verified.is_(True),
            )
            .scalar()
        )
        return float(total or 0)

    stats = {
        "orders_today": count_since(today_start),
        "orders_week": count_since(week_start),
        "orders_month": count_since(month_start),
        "revenue_today": revenue_since(today_start),
        "revenue_week": revenue_since(week_start),
        "revenue_month": revenue_since(month_start),
        "currently_processing": Order.query.filter_by(status="processing").count(),
        "awaiting_payment": Order.query.filter_by(status="awaiting_payment").count(),
        "completed_total": Order.query.filter_by(status="completed").count(),
        "failed_total": Order.query.filter_by(status="failed").count(),
        "active_workers": len(load_sessions()),
        "dead_workers": _dead_worker_count(),
    }

    total_finished = stats["completed_total"] + stats["failed_total"]
    stats["success_rate"] = (
        round(stats["completed_total"] * 100 / total_finished, 1)
        if total_finished
        else 0
    )

    recent_orders = (
        Order.query.order_by(Order.created_at.desc()).limit(10).all()
    )
    recent_failures_cutoff = now - timedelta(days=7)
    recent_failures = (
        Order.query.filter(
            Order.status == "failed",
            Order.created_at >= recent_failures_cutoff,
        )
        .order_by(Order.created_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent_orders=recent_orders,
        recent_failures=recent_failures,
    )


# --- Orders ---


@admin_bp.route("/orders")
@login_required
def orders():
    q = Order.query

    status = request.args.get("status")
    tier = request.args.get("tier")
    search = request.args.get("q", "").strip()

    if status:
        q = q.filter(Order.status == status)
    if tier:
        q = q.filter(Order.tier == tier)
    if search:
        like = f"%{search}%"
        q = q.filter(
            (Order.channel_link.like(like))
            | (Order.token.like(like))
            | (Order.ip_address.like(like))
        )

    page = max(int(request.args.get("page", 1)), 1)
    per_page = 50
    total = q.count()
    items = (
        q.order_by(Order.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return render_template(
        "admin/orders.html",
        orders=items,
        total=total,
        page=page,
        per_page=per_page,
        status=status,
        tier=tier,
        search=search,
    )


@admin_bp.route("/orders/<int:order_id>/delete", methods=["POST"])
@login_required
def delete_order(order_id):
    order = db.session.get(Order, order_id)
    if order:
        if order.file_path and os.path.exists(order.file_path):
            try:
                os.remove(order.file_path)
            except Exception:
                pass
        db.session.delete(order)
        db.session.commit()
    return redirect(request.referrer or url_for("admin.orders"))


# --- Workers ---


@admin_bp.route("/workers")
@login_required
def workers():
    active = load_sessions()
    dead = _load_dead_sessions()

    stats_rows = (
        db.session.query(
            Order.worker_used,
            func.count(Order.id),
            func.sum(
                case((Order.status == "completed", 1), else_=0)
            ).label("success"),
            func.sum(
                case((Order.status == "failed", 1), else_=0)
            ).label("fail"),
            func.sum(Order.message_count).label("messages"),
            func.max(Order.created_at).label("last_used"),
        )
        .filter(Order.worker_used.isnot(None))
        .group_by(Order.worker_used)
        .all()
    )

    stats_by_worker = {
        row[0]: {
            "total": row[1] or 0,
            "success": int(row[2] or 0),
            "fail": int(row[3] or 0),
            "messages": int(row[4] or 0),
            "last_used": row[5],
        }
        for row in stats_rows
    }

    workers_list = []
    for name, sstring in active.items():
        s = stats_by_worker.get(name, {})
        workers_list.append(
            {
                "name": name,
                "session_preview": (sstring[:18] + "...") if sstring else "",
                "total": s.get("total", 0),
                "success": s.get("success", 0),
                "fail": s.get("fail", 0),
                "messages": s.get("messages", 0),
                "last_used": s.get("last_used"),
            }
        )
    workers_list.sort(key=lambda w: w["total"], reverse=True)

    return render_template(
        "admin/workers.html",
        workers=workers_list,
        dead=dead,
    )


@admin_bp.route("/workers/add", methods=["POST"])
@login_required
def add_worker():
    name = request.form.get("name", "").strip()
    session_string = request.form.get("session_string", "").strip()
    if not name or len(session_string) < 20:
        flash("Invalid worker name or session string.", "error")
        return redirect(url_for("admin.workers"))

    data = load_sessions()
    data[name] = session_string
    with open(SESSION_FILE, "w") as f:
        json.dump(data, f, indent=2)
    flash(f"Worker {name} added.", "success")
    return redirect(url_for("admin.workers"))


@admin_bp.route("/workers/<name>/remove", methods=["POST"])
@login_required
def remove_worker(name):
    data = load_sessions()
    if name in data:
        del data[name]
        with open(SESSION_FILE, "w") as f:
            json.dump(data, f, indent=2)
        flash(f"Worker {name} removed.", "success")
    return redirect(url_for("admin.workers"))


# --- Payments ---


@admin_bp.route("/payments")
@login_required
def payments():
    paid_orders = (
        Order.query.filter(Order.tier == "paid")
        .order_by(Order.created_at.desc())
        .limit(200)
        .all()
    )
    return render_template("admin/payments.html", orders=paid_orders)


@admin_bp.route("/payments/<int:order_id>/manual_verify", methods=["POST"])
@login_required
def manual_verify(order_id):
    order = db.session.get(Order, order_id)
    if order:
        order.payment_verified = True
        order.payment_verified_at = datetime.utcnow()
        if order.status == "awaiting_payment":
            order.status = "queued"
            order.status_message = "Payment manually verified, queued."
        db.session.commit()
        flash(f"Order #{order.id} marked as paid.", "success")
    return redirect(url_for("admin.payments"))


# --- API for live charts ---


@admin_bp.route("/api/stats/hourly")
@login_required
def hourly_stats():
    since = datetime.utcnow() - timedelta(hours=24)
    rows = (
        db.session.query(
            func.strftime("%Y-%m-%d %H:00", Order.created_at),
            func.count(Order.id),
        )
        .filter(Order.created_at >= since)
        .group_by(func.strftime("%Y-%m-%d %H:00", Order.created_at))
        .all()
    )
    return jsonify({"data": [{"hour": r[0], "count": r[1]} for r in rows]})


# --- Helpers ---


def _load_dead_sessions():
    if not os.path.exists(DEAD_SESSION_FILE):
        return {}
    try:
        with open(DEAD_SESSION_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _dead_worker_count():
    return len(_load_dead_sessions())
