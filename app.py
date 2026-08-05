import asyncio
import json
import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from io import BytesIO

import qrcode
from flask import Flask, jsonify, redirect, render_template, request, send_file
from jinja2 import pass_context
from jinja2.exceptions import TemplateNotFound
from markupsafe import Markup

import config
from admin import admin_bp
from crypto_utils import verify_payment
from models import Order, db
from scraper_engine import get_channel_count, process_scraping
from translations import STRINGS, js_dict


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
        ("network", "VARCHAR(10) DEFAULT 'TRC20'"),
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


def _template_exists(app, tpl):
    """True if a template file can be loaded (used to gate untranslated RU pages
    so a missing ru/ file 404s cleanly instead of 500ing with TemplateNotFound)."""
    try:
        app.jinja_env.get_template(tpl)
        return True
    except TemplateNotFound:
        return False


def _u(path, lang):
    """Lang-aware internal-link rewriter (registered as the Jinja global `u`).
    RU mirror of an EN path is '/ru' + path, with '/' -> '/ru/'. Fragment-only
    and external/mailto hrefs pass through unchanged."""
    if lang != "ru":
        return path
    if path.startswith("#") or path.startswith("mailto:") or "://" in path:
        return path
    return "/ru/" if path == "/" else "/ru" + path


# Blog posts: ONE slug set; EN + RU title/excerpt live side by side so the RU
# blog index lists Russian headlines.
BLOG_POSTS = [
    {
        "slug": "how-to-export-telegram-channel-to-csv",
        "title": "How to Export a Telegram Channel to CSV (4 Methods Compared)",
        "excerpt": "Four ways to export a public Telegram channel's message history to CSV, from one-click web tools to Python scripts. Pros, cons, and when to use each.",
        "title_ru": "Как экспортировать Telegram-канал в CSV (сравнение 4 способов)",
        "excerpt_ru": "Четыре способа выгрузить историю сообщений публичного Telegram-канала в CSV — от веб-сервисов в один клик до Python-скриптов. Плюсы, минусы и когда что использовать.",
        "date": "2026-05-12",
        "date_human": "May 12, 2026",
        "read_time": "8",
    },
    {
        "slug": "telegram-channel-backup-methods",
        "title": "Telegram Channel Backup Methods (2026): The Complete Guide",
        "excerpt": "Every realistic way to back up a Telegram channel in 2026 — text, media, screenshots — with pros, cons, and a recommendation per use case.",
        "title_ru": "Способы резервного копирования Telegram-канала (2026): полное руководство",
        "excerpt_ru": "Все реальные способы сделать бэкап Telegram-канала в 2026 году — текст, медиа, скриншоты — с плюсами, минусами и рекомендацией под каждый сценарий.",
        "date": "2026-05-12",
        "date_human": "May 12, 2026",
        "read_time": "10",
    },
]


def _register_public_routes(app):
    # --- i18n: render a translation value through Jinja so the placeholders /
    # conditionals embedded INSIDE the string (e.g. {{ free_limit }}, {% if
    # paid_max %}) evaluate against the live page context. Returns Markup so the
    # inline HTML in some values (<br>, <small>, <strong>, <a>, <code>) is not
    # re-escaped. Registered as the global `tr`. ---
    @pass_context
    def _tr(ctx, key):
        t = ctx.get("t") or STRINGS["en"]
        raw = t.get(key, STRINGS["en"].get(key, ""))
        if ("{{" in raw) or ("{%" in raw):
            raw = ctx.environment.from_string(raw).render(ctx.get_all())
        return Markup(raw)

    @pass_context
    def _tr_raw(ctx, key):
        """Like tr() but returns the rendered PLAIN string (not Markup), for use
        inside |jsonld where we want json.dumps (not HTML-safe) escaping so the
        JSON-LD stays byte-identical to the hand-written English."""
        t = ctx.get("t") or STRINGS["en"]
        raw = t.get(key, STRINGS["en"].get(key, ""))
        if ("{{" in raw) or ("{%" in raw):
            raw = ctx.environment.from_string(raw).render(ctx.get_all())
        return str(raw)

    def _jsonld(value):
        # Plain JSON string literal (ensure_ascii=False keeps Cyrillic readable,
        # ensures valid JSON without HTML-entity-escaping quotes/apostrophes).
        return Markup(json.dumps(str(value), ensure_ascii=False))

    app.jinja_env.globals["u"] = _u
    app.jinja_env.globals["tr"] = _tr
    app.jinja_env.globals["tr_raw"] = _tr_raw
    app.jinja_env.filters["jsonld"] = _jsonld

    def _home(lang):
        return render_template(
            "index.html",
            lang=lang,
            t=STRINGS[lang],
            t_js=js_dict(lang),
            alt_lang="ru" if lang == "en" else "en",
            page_path="/",
            free_limit=config.FREE_MESSAGE_LIMIT,
            paid_price=config.PAID_PRICE_USDT,
            wallet=config.WALLET_ADDRESS,
        )

    def _legal(lang, base_tpl, page_path):
        tpl = f"ru/{base_tpl}" if lang == "ru" else base_tpl
        return render_template(
            tpl,
            lang=lang,
            t=STRINGS[lang],
            alt_lang="ru" if lang == "en" else "en",
            page_path=page_path,
        )

    def _blog_index(lang):
        posts = [
            {
                **p,
                "title": p["title_ru"] if lang == "ru" else p["title"],
                "excerpt": p["excerpt_ru"] if lang == "ru" else p["excerpt"],
            }
            for p in BLOG_POSTS
        ]
        return render_template(
            "blog/index.html",
            lang=lang,
            t=STRINGS[lang],
            alt_lang="ru" if lang == "en" else "en",
            page_path="/blog",
            posts=posts,
        )

    def _blog_post(lang, slug):
        # Validate slug against known posts to prevent template-injection
        if not any(p["slug"] == slug for p in BLOG_POSTS):
            return "Post not found", 404
        tpl = f"ru/blog/{slug}.html" if lang == "ru" else f"blog/{slug}.html"
        # Guard untranslated RU posts: 404 (never 500 on TemplateNotFound).
        if lang == "ru" and not _template_exists(app, tpl):
            return "Перевод недоступен", 404
        return render_template(
            tpl,
            lang=lang,
            t=STRINGS[lang],
            alt_lang="ru" if lang == "en" else "en",
            page_path=f"/blog/{slug}",
        )

    # Register each public page under BOTH the root and the /ru/ prefix, with
    # DISTINCT endpoint names (duplicate endpoints raise at startup).
    app.add_url_rule("/", "home", lambda: _home("en"))
    app.add_url_rule("/ru/", "home_ru", lambda: _home("ru"))

    app.add_url_rule("/privacy-policy", "privacy", lambda: _legal("en", "privacy.html", "/privacy-policy"))
    app.add_url_rule("/ru/privacy-policy", "privacy_ru", lambda: _legal("ru", "privacy.html", "/privacy-policy"))

    app.add_url_rule("/terms", "terms", lambda: _legal("en", "terms.html", "/terms"))
    app.add_url_rule("/ru/terms", "terms_ru", lambda: _legal("ru", "terms.html", "/terms"))

    app.add_url_rule("/about", "about", lambda: _legal("en", "about.html", "/about"))
    app.add_url_rule("/ru/about", "about_ru", lambda: _legal("ru", "about.html", "/about"))

    app.add_url_rule("/blog", "blog_index", lambda: _blog_index("en"))
    app.add_url_rule("/ru/blog", "blog_index_ru", lambda: _blog_index("ru"))

    app.add_url_rule("/blog/<slug>", "blog_post", lambda slug: _blog_post("en", slug))
    app.add_url_rule("/ru/blog/<slug>", "blog_post_ru", lambda slug: _blog_post("ru", slug))

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
        # (en_path, priority, changefreq, ru_available). RU is always available
        # for the dictionary-driven pages; blog posts are gated on the RU file.
        pages = [
            ("/", "1.0", "weekly", True),
            ("/blog", "0.8", "weekly", True),
            ("/about", "0.6", "monthly", True),
            ("/privacy-policy", "0.5", "monthly", True),
            ("/terms", "0.5", "monthly", True),
        ]
        for p in BLOG_POSTS:
            ru_ok = _template_exists(app, f"ru/blog/{p['slug']}.html")
            pages.append((f"/blog/{p['slug']}", "0.7", "monthly", ru_ok))

        def _ru(path):
            return "/ru/" if path == "/" else "/ru" + path

        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += (
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        )
        for en_path, priority, changefreq, ru_ok in pages:
            en_url = base + en_path
            ru_url = base + _ru(en_path)
            # Shared en/ru/x-default alternates triad (identical on both URLs).
            alts = (
                f'    <xhtml:link rel="alternate" hreflang="en" href="{en_url}"/>\n'
            )
            if ru_ok:
                alts += (
                    f'    <xhtml:link rel="alternate" hreflang="ru" href="{ru_url}"/>\n'
                )
            alts += (
                f'    <xhtml:link rel="alternate" hreflang="x-default" href="{en_url}"/>\n'
            )
            locs = [en_url]
            if ru_ok:
                locs.append(ru_url)
            for loc in locs:
                xml += (
                    "  <url>\n"
                    f"    <loc>{loc}</loc>\n"
                    f"{alts}"
                    f"    <lastmod>{today}</lastmod>\n"
                    f"    <changefreq>{changefreq}</changefreq>\n"
                    f"    <priority>{priority}</priority>\n"
                    "  </url>\n"
                )
        xml += "</urlset>\n"
        return xml, 200, {"Content-Type": "application/xml"}

    @app.route("/qr/wallet.png")
    def wallet_qr_legacy():
        # Back-compat for any cached references to the old single-wallet QR.
        return redirect(f"/qr/{config.DEFAULT_NETWORK}.png", code=302)

    @app.route("/qr/<network>.png")
    def wallet_qr(network):
        net = config.USDT_NETWORKS.get((network or "").upper())
        if not net or not net.get("wallet"):
            return "Wallet not configured", 404
        img = qrcode.make(net["wallet"], box_size=10, border=2)
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
            network = (data.get("network") or config.DEFAULT_NETWORK).upper()
            if network not in config.USDT_NETWORKS:
                network = config.DEFAULT_NETWORK

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
                network=network,
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
                    "amount": price,
                    "currency": "USDT",
                    "message_count": total_count,
                    "billable": billable,
                    "capped": total_count > billable,
                }
                # All networks share the same price; the widget lets the user pick one.
                response["networks"] = [
                    {
                        "id": k,
                        "label": v["label"],
                        "short": v["short"],
                        "wallet": v["wallet"],
                        "qr": f"/qr/{k}.png",
                        "fee_note": v["fee_note"],
                    }
                    for k, v in config.USDT_NETWORKS.items()
                    if v.get("wallet")
                ]
                response["default_network"] = config.DEFAULT_NETWORK
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
            network = (data.get("network") or "").upper()
            if not token or not txid:
                return jsonify({"error": "Missing token or txid."}), 400

            order = Order.query.filter_by(token=token).first()
            if not order:
                return jsonify({"error": "Order not found."}), 404
            if order.tier != "paid":
                return jsonify({"error": "This order does not require payment."}), 400
            if order.payment_verified:
                return jsonify({"success": True, "message": "Already verified."})

            # The client picks WHICH chain to check; the wallet/contract/decimals
            # all come from server config, never from the client.
            if network not in config.USDT_NETWORKS:
                network = order.network or config.DEFAULT_NETWORK

            existing = Order.query.filter(Order.txid == txid, Order.id != order.id).first()
            if existing:
                return jsonify({"error": "This TXID has already been used."}), 400

            ok, reason = verify_payment(network, txid, order.amount)
            if not ok:
                # Do NOT persist the txid on failure — it's a UNIQUE column and a
                # failed attempt must not reserve/block its legitimate later use.
                return jsonify({"success": False, "error": reason}), 400

            try:
                order.network = network
                order.txid = txid
                order.payment_verified = True
                order.payment_verified_at = datetime.utcnow()
                order.status = "queued"
                order.status_message = "Payment verified, queued."
                db.session.commit()
            except Exception:
                # UNIQUE(txid) lost a race with a parallel submit -> treat as reused.
                db.session.rollback()
                return jsonify({"error": "This TXID has already been used."}), 400

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
