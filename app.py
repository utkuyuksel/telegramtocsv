import asyncio
import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from io import BytesIO

import qrcode
from flask import Flask, jsonify, render_template, request, send_file

import config
from admin import admin_bp
from crypto_utils import verify_txid
from models import Order, db
from scraper_engine import get_channel_count, process_scraping


def create_app():
    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
    app.config["SQLALCHEMY_DATABASE_URI"] = config.DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.permanent_session_lifetime = timedelta(days=7)

    db.init_app(app)

    with app.app_context():
        os.makedirs(config.DOWNLOADS_DIR, exist_ok=True)
        db.create_all()
        _migrate_sqlite_schema(app)

    app.register_blueprint(admin_bp)
    _register_public_routes(app)

    threading.Thread(target=_cleanup_loop, daemon=True).start()
    return app


# --- DB migration ---


def _migrate_sqlite_schema(app):
    """Add columns added after the initial schema. SQLite only."""
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if not uri.startswith("sqlite:///"):
        return
    db_path = uri.replace("sqlite:///", "")
    if not os.path.isabs(db_path):
        db_path = os.path.join(app.instance_path, db_path)
    if not os.path.exists(db_path):
        return

    new_columns = [
        ("payment_verified", "BOOLEAN DEFAULT 0"),
        ("payment_verified_at", "DATETIME"),
        ("user_agent", "VARCHAR(255)"),
        ("worker_used", "VARCHAR(50)"),
        ("message_count", "INTEGER DEFAULT 0"),
        ("total_messages", "INTEGER DEFAULT 0"),
        ("completed_at", "DATETIME"),
        ("file_format", "VARCHAR(10) DEFAULT 'csv'"),
    ]

    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        cur.execute("PRAGMA table_info(orders)")
        existing = {row[1] for row in cur.fetchall()}
        for name, ddl in new_columns:
            if name not in existing:
                cur.execute(f"ALTER TABLE orders ADD COLUMN {name} {ddl}")
        con.commit()
    finally:
        con.close()


# --- Background cleanup ---


def _cleanup_loop():
    folder = config.DOWNLOADS_DIR
    cutoff_seconds = config.FILE_RETENTION_HOURS * 3600
    while True:
        try:
            time.sleep(3600)
            cutoff = time.time() - cutoff_seconds
            if not os.path.exists(folder):
                continue
            for f in os.listdir(folder):
                path = os.path.join(folder, f)
                if os.path.isfile(path) and os.path.getmtime(path) < cutoff:
                    try:
                        os.remove(path)
                    except Exception:
                        pass
        except Exception:
            pass


# --- Request helpers ---


def _client_ip():
    """Real client IP. Behind Cloudflare, CF-Connecting-IP can't be spoofed by the
    visitor; fall back to the first X-Forwarded-For hop, then remote_addr."""
    cf = request.headers.get("CF-Connecting-IP")
    if cf:
        return cf.strip()
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.remote_addr


# --- DB helper ---


def _safe_db_commit(app_context, order_id, updates):
    try:
        with app_context:
            order = db.session.get(Order, order_id)
            if not order:
                return
            for key, value in updates.items():
                setattr(order, key, value)
            db.session.commit()
    except Exception:
        pass


# --- Scraper runner ---


def _run_scraping(app_context, order_id):
    _safe_db_commit(
        app_context,
        order_id,
        {
            "status": "processing",
            "progress": 5,
            "status_message": "Connecting to server...",
        },
    )

    def update_progress(percent, message):
        _safe_db_commit(
            app_context, order_id, {"progress": percent, "status_message": message}
        )

    def record_worker(worker_name):
        _safe_db_commit(app_context, order_id, {"worker_used": worker_name})

    try:
        with app_context:
            order = db.session.get(Order, order_id)
            if not order:
                return
            target_link = order.channel_link
            target_token = order.token
            tier = order.tier
            fmt = order.file_format or "csv"

        # Paid tier exports the WHOLE channel (no cap); free tier is limited.
        limit = None if tier == "paid" else config.FREE_MESSAGE_LIMIT

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result_path, message_count, total_count = loop.run_until_complete(
                process_scraping(
                    target_link,
                    target_token,
                    limit=limit,
                    fmt=fmt,
                    progress_callback=update_progress,
                    worker_callback=record_worker,
                )
            )
        finally:
            loop.close()

        if result_path and os.path.exists(result_path):
            status_msg = f"File ready! Exported {message_count:,} messages."
            _safe_db_commit(
                app_context,
                order_id,
                {
                    "status": "completed",
                    "progress": 100,
                    "status_message": status_msg,
                    "file_path": result_path,
                    "message_count": message_count,
                    "total_messages": total_count,
                    "completed_at": datetime.utcnow(),
                },
            )
        else:
            _safe_db_commit(
                app_context,
                order_id,
                {
                    "status": "failed",
                    "status_message": "Could not fetch Telegram data. Channel may be private or empty.",
                    "message_count": message_count,
                    "total_messages": total_count,
                },
            )
    except Exception:
        _safe_db_commit(
            app_context,
            order_id,
            {
                "status": "failed",
                "status_message": "System busy, please try again later.",
            },
        )


# --- Public routes ---


def _register_public_routes(app):
    @app.route("/")
    def home():
        return render_template(
            "index.html",
            free_limit=config.FREE_MESSAGE_LIMIT,
            paid_price=config.PAID_PRICE_USDT,
            wallet=config.WALLET_ADDRESS,
        )

    @app.route("/privacy-policy")
    def privacy():
        return render_template("privacy.html")

    @app.route("/terms")
    def terms():
        return render_template("terms.html")

    @app.route("/about")
    def about():
        return render_template("about.html")

    # Blog
    BLOG_POSTS = [
        {
            "slug": "how-to-export-telegram-channel-to-csv",
            "title": "How to Export a Telegram Channel to CSV (4 Methods Compared)",
            "excerpt": "Four ways to export a public Telegram channel's message history to CSV, from one-click web tools to Python scripts. Pros, cons, and when to use each.",
            "date": "2026-05-12",
            "date_human": "May 12, 2026",
            "read_time": "8",
        },
        {
            "slug": "telegram-channel-backup-methods",
            "title": "Telegram Channel Backup Methods (2026): The Complete Guide",
            "excerpt": "Every realistic way to back up a Telegram channel in 2026 — text, media, screenshots — with pros, cons, and a recommendation per use case.",
            "date": "2026-05-12",
            "date_human": "May 12, 2026",
            "read_time": "10",
        },
    ]

    @app.route("/blog")
    def blog_index():
        return render_template("blog/index.html", posts=BLOG_POSTS)

    @app.route("/blog/<slug>")
    def blog_post(slug):
        # Validate slug against known posts to prevent template-injection
        if not any(p["slug"] == slug for p in BLOG_POSTS):
            return "Post not found", 404
        return render_template(f"blog/{slug}.html")

    @app.route("/favicon.svg")
    def favicon_svg():
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
            '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
            '<stop offset="0" stop-color="#0EA5E9"/>'
            '<stop offset="1" stop-color="#38BDF8"/>'
            '</linearGradient></defs>'
            '<rect width="64" height="64" rx="14" fill="url(#g)"/>'
            '<path d="M32 18v22m0 0l-9-9m9 9l9-9" stroke="white" '
            'stroke-width="6" stroke-linecap="round" stroke-linejoin="round" fill="none"/>'
            '</svg>'
        )
        return svg, 200, {"Content-Type": "image/svg+xml", "Cache-Control": "public, max-age=604800"}

    @app.route("/favicon.ico")
    def favicon_ico():
        return "", 204

    @app.route("/ads.txt")
    def ads_txt():
        return (
            f"google.com, {config.ADSENSE_PUB_ID}, DIRECT, f08c47fec0942fa0",
            200,
            {"Content-Type": "text/plain"},
        )

    @app.route("/robots.txt")
    def robots_txt():
        body = (
            "User-agent: *\n"
            "Allow: /\n"
            "Disallow: /admin/\n"
            "Disallow: /api/\n"
            "Disallow: /download/\n"
            "Disallow: /qr/\n"
            "\n"
            "Sitemap: https://telegramtocsv.com/sitemap.xml\n"
        )
        return body, 200, {"Content-Type": "text/plain"}

    @app.route("/sitemap.xml")
    def sitemap_xml():
        base = "https://telegramtocsv.com"
        today = datetime.utcnow().strftime("%Y-%m-%d")
        urls = [
            (f"{base}/", "1.0", "weekly"),
            (f"{base}/blog", "0.8", "weekly"),
            (f"{base}/blog/how-to-export-telegram-channel-to-csv", "0.7", "monthly"),
            (f"{base}/blog/telegram-channel-backup-methods", "0.7", "monthly"),
            (f"{base}/about", "0.6", "monthly"),
            (f"{base}/privacy-policy", "0.5", "monthly"),
            (f"{base}/terms", "0.5", "monthly"),
        ]
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        for loc, priority, changefreq in urls:
            xml += (
                "  <url>\n"
                f"    <loc>{loc}</loc>\n"
                f"    <lastmod>{today}</lastmod>\n"
                f"    <changefreq>{changefreq}</changefreq>\n"
                f"    <priority>{priority}</priority>\n"
                "  </url>\n"
            )
        xml += "</urlset>\n"
        return xml, 200, {"Content-Type": "application/xml"}

    @app.route("/qr/wallet.png")
    def wallet_qr():
        if not config.WALLET_ADDRESS:
            return "Wallet not configured", 404
        img = qrcode.make(config.WALLET_ADDRESS, box_size=10, border=2)
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return send_file(buf, mimetype="image/png", max_age=300)

    @app.route("/api/create_order", methods=["POST"])
    def create_order():
        try:
            data = request.json or {}
            channel = (data.get("channel") or "").strip()
            tier = (data.get("tier") or "free").lower()
            if tier not in ("free", "paid"):
                tier = "free"
            fmt = (data.get("format") or "csv").lower()
            if fmt not in ("csv", "xlsx"):
                fmt = "csv"

            user_ip = _client_ip()
            user_agent = request.headers.get("User-Agent", "")[:255]

            if not channel:
                return jsonify({"error": "Please enter a valid Telegram channel link."}), 400

            if tier == "free":
                last_24h = datetime.utcnow() - timedelta(days=1)
                daily_count = Order.query.filter(
                    Order.ip_address == user_ip,
                    Order.created_at >= last_24h,
                    Order.tier == "free",
                ).count()
                if daily_count >= config.DAILY_IP_LIMIT:
                    return jsonify({"error": "Daily limit reached. Try again tomorrow or upgrade to paid."}), 429

            # Paid tier is priced by channel size: validate the channel and fetch its
            # message count up front so the user gets an exact quote BEFORE paying.
            price = 0.0
            total_count = 0
            billable = 0
            if tier == "paid":
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    total_count, err = loop.run_until_complete(get_channel_count(channel))
                finally:
                    loop.close()
                if err:
                    return jsonify({"error": err}), 400
                price, billable = config.price_for(total_count)

            new_order = Order(
                channel_link=channel,
                tier=tier,
                currency="USDT",
                amount=price,
                total_messages=total_count,
                file_format=fmt,
                ip_address=user_ip,
                user_agent=user_agent,
                status="awaiting_payment" if tier == "paid" else "queued",
                status_message=(
                    "Awaiting USDT payment..." if tier == "paid" else "Queued..."
                ),
            )
            db.session.add(new_order)
            db.session.commit()

            response = {"success": True, "token": new_order.token, "tier": tier}
            if tier == "paid":
                response["payment"] = {
                    "wallet": config.WALLET_ADDRESS,
                    "amount": price,
                    "currency": "USDT",
                    "network": "TRC20",
                    "message_count": total_count,
                    "billable": billable,
                    "capped": total_count > billable,
                }
            else:
                threading.Thread(
                    target=_run_scraping,
                    args=(app.app_context(), new_order.id),
                    daemon=True,
                ).start()
            return jsonify(response)
        except Exception:
            return jsonify({"error": "System error occurred."}), 500

    @app.route("/api/submit_payment", methods=["POST"])
    def submit_payment():
        try:
            data = request.json or {}
            token = (data.get("token") or "").strip()
            txid = (data.get("txid") or "").strip()
            if not token or not txid:
                return jsonify({"error": "Missing token or txid."}), 400

            order = Order.query.filter_by(token=token).first()
            if not order:
                return jsonify({"error": "Order not found."}), 404
            if order.tier != "paid":
                return jsonify({"error": "This order does not require payment."}), 400
            if order.payment_verified:
                return jsonify({"success": True, "message": "Already verified."})

            existing = Order.query.filter(Order.txid == txid, Order.id != order.id).first()
            if existing:
                return jsonify({"error": "This TXID has already been used."}), 400

            ok, reason = verify_txid(txid, order.amount, currency="USDT")
            if not ok:
                order.txid = txid
                db.session.commit()
                return jsonify({"success": False, "error": reason}), 400

            order.txid = txid
            order.payment_verified = True
            order.payment_verified_at = datetime.utcnow()
            order.status = "queued"
            order.status_message = "Payment verified, queued."
            db.session.commit()

            threading.Thread(
                target=_run_scraping,
                args=(app.app_context(), order.id),
                daemon=True,
            ).start()
            return jsonify({"success": True})
        except Exception:
            return jsonify({"error": "System error occurred."}), 500

    @app.route("/api/check_status/<token>", methods=["GET"])
    def check_status(token):
        try:
            order = Order.query.filter_by(token=token).first()
            if not order:
                return jsonify({"success": False, "error": "Not found"}), 404
            return jsonify(
                {
                    "success": True,
                    "data": {
                        "status": order.status,
                        "progress": order.progress,
                        "status_message": order.status_message,
                        "tier": order.tier,
                        "payment_verified": order.payment_verified,
                    },
                }
            )
        except Exception:
            return jsonify({"success": False}), 500

    @app.route("/download/<token>", methods=["GET"])
    def download_file(token):
        try:
            order = Order.query.filter_by(token=token).first()
            if not order or order.status != "completed":
                return "File not ready", 404
            if not order.file_path or not os.path.exists(order.file_path):
                return "File expired or deleted", 404
            return send_file(
                order.file_path,
                as_attachment=True,
                download_name=os.path.basename(order.file_path),
            )
        except Exception as e:
            return f"Error: {e}", 500


app = create_app()


if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT, debug=False)
