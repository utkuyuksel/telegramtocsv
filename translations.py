# -*- coding: utf-8 -*-
"""
UI-chrome + landing-page translations for TelegramtoCSV.

STRINGS = {"en": {...}, "ru": {...}} — one FLAT dict per language, keyed by a
stable, readable string id. Templates reference these via {{ t.KEY }} (plain
text) or {{ t.KEY|safe }} (values that contain inline HTML tags).

GROUND-TRUTH RULE: the "en" values here are byte-for-byte the exact strings that
the live English templates render today. The English output MUST NOT change —
this module only ADDS a Russian layer. The "ru" values come from the supplied
_ru_build.json (units: index_head, index_tool, index_sections, index_faq,
chrome); where a current live string was not present in that JSON (e.g. the
multi-network payment widget, the "Use cases" block, "Frequently asked
questions"), an in-style Russian translation is supplied and noted in JS_KEYS /
the agent report.

Jinja placeholders ({{ free_limit }}, {{ '%.2f' % paid_price }}, {% if %} …) are
preserved verbatim INSIDE the string values and are re-rendered by Jinja because
the templates pass these through a second render (the values are emitted via a
small {% with %}/{{ ... }} render, see template usage). For the JS-facing keys
(JS_KEYS) the values are pure UI text with NO Jinja and are shipped to the
browser once as `const T = {{ t_js|tojson }}`.
"""

# --- Keys whose VALUES are surfaced to client-side JS (shipped via t_js|tojson).
# These must be plain UI text (no Jinja, no HTML) so JSON-encoding is safe and
# Russian quotes/apostrophes never break the script. ---
JS_KEYS = [
    "js_quote_uncapped",
    "js_quote_capped",
    "js_pay_verified",
    "js_verify_failed",
    "js_network_error",
    "js_dl_xlsx",
    "js_dl_csv",
    "js_dl_prefix",
    "js_copied",
    "js_export_error",
    "js_txid_placeholder",
    "js_btn_export",
]


_EN = {
    # ===================== <head> / meta / SEO (index) =====================
    "meta_title": "TelegramtoCSV — Export Public Telegram Channel History to CSV",
    "meta_description": "Export the full message history of any public Telegram channel to CSV or Excel (.xlsx) in seconds. Free sample, or the whole archive for a flat $4 (one-time). No signup, no software install.",
    "meta_keywords": "telegram to csv, export telegram channel, scrape telegram, telegram archive, telegram data export, telegram channel csv",
    "og_title": "TelegramtoCSV — Export Telegram Channels to CSV",
    "og_description": "Download the entire message history of any public Telegram channel as CSV or Excel. Fast, secure, no signup.",

    # JSON-LD text (index)
    "ld_org_description": "Independent tool for exporting public Telegram channel histories into CSV and Excel (.xlsx) files.",
    "ld_webapp_description": "Export the message history of public Telegram channels into a downloadable CSV or Excel (.xlsx) file. Free for the first {{ free_limit }} messages, or the whole archive for a flat ${{ '%.2f' % paid_price }} USDT (one-time). No signup, no install.",
    "ld_offer_free_name": "Free tier",
    "ld_offer_free_description": "Last {{ free_limit }} messages per export, ad-supported, no signup.",
    "ld_offer_paid_name": "Unlimited",
    "ld_offer_paid_description": "Full channel archive, ad-free, one-time payment in USDT on TRC20 (TRON) network.",
    "ld_feature_list": "CSV and Excel (.xlsx) export with message ID and date and content and view count and direct link, free tier without signup, auto-delete after 1 hour, public channels only, in-browser instant download",

    # JSON-LD FAQPage (index) — short variants used in the structured data
    "ld_faq_q1": "Is this legal?",
    "ld_faq_a1": "Yes. We only access public Telegram channels — the exact same data anyone with a Telegram account can already read. We don't break into private chats, bypass passwords, or hack anyone. We just put the data into a more usable format.",
    "ld_faq_q2": "Do you store my exported file?",
    "ld_faq_a2": "Only briefly. After your CSV is generated, it sits on our server for at most one hour and is then permanently deleted. Your download link stops working after that window. We don't keep any copy.",
    "ld_faq_q3": "What's actually in the CSV?",
    "ld_faq_a3": "Every message gets one row with: message ID, date/time (UTC), content (text or caption; [Media/File] for non-text), view count, and a direct link back to the original message. Media attachments are not downloaded.",
    "ld_faq_q4": "What does public channel mean?",
    "ld_faq_a4": "A channel that anyone can join or read without an invite. If you can see the channel's messages on the web at t.me/channel_name without logging in, it's public. Private channels (requiring an invite link or admin approval) cannot be exported.",
    "ld_faq_q5": "Why USDT for payment?",
    "ld_faq_a5": "USDT on the TRON network is fast (under a minute), cheap (often less than $0.10 in fees) and instantly verifiable on-chain. We're a small tool, not a Stripe-grade business — crypto lets us keep the price low without payment processor cuts.",
    "ld_faq_q6": "My free limit isn't enough. Do I get a discount on Unlimited?",
    "ld_faq_a6": "Unlimited is a flat one-time ${{ '%.2f' % paid_price }} for any channel, whatever its size. No subscription, no surprise extras.",
    "ld_faq_q7": "Can you export media (photos, videos)?",
    "ld_faq_a7": "Not currently. The CSV contains text content, timestamps, view counts and links — but not the actual media files. We may add a media-zip option in the future.",
    "ld_faq_q8": "How long does an unlimited export take?",
    "ld_faq_a8": "Roughly 1,000 messages per 5 seconds on average. A 50,000-message channel takes about 4-5 minutes. Larger channels are slower because we rotate through multiple worker accounts to avoid rate limits.",
    "ld_faq_q9": "Is there a limit on channel size?",
    "ld_faq_a9": "No. The Unlimited tier exports the whole channel, of any size — there is no message cap, and it's a flat ${{ '%.2f' % paid_price }} no matter how big. Very large channels simply take a little longer to process.",

    # ===================== NAV (index) =====================
    "nav_features": "Features",
    "nav_how": "How it works",
    "nav_pricing": "Pricing",
    "nav_faq": "FAQ",
    "nav_blog": "Blog",
    "nav_about": "About",
    "nav_export_now": "Export now",
    "aria_toggle_dark": "Toggle dark mode",

    # ===================== HERO =====================
    "hero_pill": "No signup · Files auto-deleted after 1 hour",
    # H1 contains an inline <br> — rendered with |safe
    "hero_h1": "Export any public Telegram channel<br>to CSV or Excel",
    "hero_sub": "Download the entire message history of a public Telegram channel — messages, dates, view counts and links — in seconds. Free for the first {{ free_limit }} messages, or unlock the full history for a flat ${{ '%.2f' % paid_price }} — any channel, any size.",
    "hero_cta_primary": "Start exporting",
    "hero_cta_secondary": "View pricing",
    "trust_no_account": "No account required",
    "trust_autodelete": "Auto-deleted after 1 hour",
    "trust_any_channel": "Works with any public channel",

    # ===================== TOOL CARD =====================
    "tool_step1": "1 · Choose your plan",
    "tier_free_name": "Free",
    "tier_free_price": "$0",
    "tier_free_desc": "Quick exports with ad support · perfect for a single sample",
    "tier_free_feat1": "Last {{ free_limit }} messages",
    "tier_free_feat2": "CSV with views &amp; links",
    "tier_free_feat3": "No signup required",
    "tier_free_feat4": "Auto-delete in 1 hour",
    "tier_paid_name": "Unlimited",
    "badge_best": "BEST VALUE",
    "tier_paid_price": "${{ '%.2f' % paid_price }} <small>one-time</small>",
    "tier_paid_desc": "Whole archive · flat one-time price · USDT",
    "tier_paid_feat1": "Entire channel history",
    "tier_paid_feat2": "No message cap",
    "tier_paid_feat3": "Ad-free experience",
    "tier_paid_feat4": "Priority worker queue",
    "tool_step2": "2 · Paste the channel link",
    "channel_placeholder": "https://t.me/channel_name",
    "btn_export": "Export",
    "tool_step3": "3 · Choose file format",
    "fmt_csv": "CSV <small>.csv</small>",
    "fmt_xlsx": "Excel <small>.xlsx</small>",

    # Progress
    "progress_processing": "Processing",
    "progress_connecting": "Connecting…",

    # Payment widget
    "pay_head": "Payment required",
    # net-tab labels (multi-network widget — not in _ru_build.json, added in-style)
    "net_trc20": "TRON · TRC20",
    "net_trc20_tag": "cheapest",
    "net_bep20": "BSC · BEP20",
    "net_bep20_tag": "low fee",
    "net_erc20": "Ethereum · ERC20",
    "net_erc20_tag": "high gas",
    "pay_gas_warn": "⚠ Ethereum network fees (paid by you) are typically $1–5+ — often more than the export itself. Use <strong>TRON</strong> or <strong>BSC</strong> to pay far less.",
    "pay_sub": "Send <strong><span id=\"paySendAmt\">{{ '%.2f' % paid_price }}</span> USDT</strong> on the <strong><span id=\"payNetName\">TRON (TRC20)</span></strong> network\n                    to the wallet below. Scan the QR with your crypto wallet app, or copy the address manually.",
    "pay_qr_label": "Scan to pay",
    "pay_qr_alt": "USDT wallet QR code",
    "pay_qr_hint": "Open <strong>Trust Wallet</strong>, <strong>Binance</strong>, <strong>Bybit</strong>,\n                        or any USDT-compatible wallet, choose USDT on the selected network, scan this code, and enter\n                        <strong><span id=\"payScanAmt\">{{ '%.2f' % paid_price }}</span> USDT</strong> as the amount.",
    "pay_amount_label": "Amount",
    # wallet row label — the network code is a live <span id="payNetLabel"> updated by JS
    "pay_wallet_label_pre": "Wallet (",
    "pay_wallet_label_post": ")",
    "btn_copy": "Copy",
    "btn_verify": "Verify",

    # Download block (static HTML)
    "download_complete": "Export complete",
    "download_ready": "Your file is ready. The link expires in 1 hour.",
    "download_file": "Download file",

    # ===================== FEATURES =====================
    "features_eyebrow": "Features",
    "features_heading": "Everything you need to archive a channel",
    "features_intro": "Built for researchers, marketers and data analysts who need clean, structured data — not screenshots.",
    "feat1_title": "Structured CSV output",
    "feat1_text": "Every message exported as a row with ID, timestamp, content, view count, and direct link. Download as CSV or Excel (.xlsx) — opens in Excel, Sheets, pandas, anywhere.",
    "feat2_title": "Full history, not just recent posts",
    "feat2_text": "Most tools cap at a few hundred messages. With the unlimited plan, we pull the whole archive — even channels with 100,000+ posts.",
    "feat3_title": "Fast & rate-limit-resistant",
    "feat3_text": "Distributed across many worker accounts to avoid Telegram's flood limits. A 10,000-message channel finishes in under a minute.",
    "feat4_title": "Privacy by design",
    "feat4_text": "No signup, no email, no tracking cookies. Your exported file is automatically deleted from our servers after one hour.",
    "feat5_title": "Browser-based, zero install",
    "feat5_text": "Works in any modern browser on desktop or mobile. No software to install, no Python scripts to configure, no API keys to manage.",
    "feat6_title": "Public channels only",
    "feat6_text": "We only access publicly accessible content — the same data anyone could view in their Telegram app. No private chats, no private channels.",

    # ===================== HOW IT WORKS =====================
    "how_eyebrow": "How it works",
    "how_heading": "Three steps, under a minute",
    "step1_title": "Paste the channel link",
    "step1_text": "Copy the public Telegram channel URL (looks like <code>t.me/channel_name</code>) and paste it into the export box at the top of this page.",
    "step2_title": "Choose free or unlimited",
    "step2_text": "Free covers the last {{ free_limit }} messages — perfect for a quick look. The unlimited plan pulls the whole history for a flat ${{ '%.2f' % paid_price }} in USDT — one payment, any channel size.",
    "step3_title": "Download your CSV",
    "step3_text": "We scrape and serve your file as CSV or Excel (.xlsx). Open it in Excel, Google Sheets, Notion, or feed it to your favorite data tool.",

    # ===================== PRICING =====================
    "pricing_eyebrow": "Pricing",
    "pricing_heading": "Simple, transparent pricing",
    "pricing_intro": "Try it free first. Upgrade only when you need the full archive.",
    "price_free_title": "Free",
    "price_free_price": "$0",
    "price_free_sub": "Forever · ad-supported",
    "price_free_feat1": "Last {{ free_limit }} messages",
    "price_free_feat2": "CSV export with views & links",
    "price_free_feat3": "No signup required",
    "price_free_feat4": "Auto-delete in 1 hour",
    "price_free_feat5": "Limited to 100 exports per day per IP",
    "price_free_cta": "Get started free",
    "price_paid_title": "Unlimited",
    "price_paid_price": "${{ '%.2f' % paid_price }}",
    "price_paid_sub": "One-time · any channel size",
    "price_paid_feat1": "Entire channel history*",
    "price_paid_feat2": "Ad-free experience",
    "price_paid_feat3": "Pay in USDT (TRC20)",
    "price_paid_feat4": "Same CSV format, fully complete",
    "price_paid_feat5": "Priority worker queue",
    "price_paid_cta": "Choose Unlimited",
    "price_paid_footnote": "* Flat ${{ '%.2f' % paid_price }} for any channel, any size — no per-message pricing, no cap. Choose <a href=\"#faq\" style=\"color: var(--muted-2); text-decoration: underline;\">CSV or Excel</a>.",

    # ===================== USE CASES (not in _ru_build.json — added in-style) =====================
    "uses_eyebrow": "Use cases",
    "uses_heading": "Who exports Telegram data?",
    "use1_title": "Researchers",
    "use1_text": "Sentiment analysis, timeline reconstruction, longitudinal studies on public discourse.",
    "use2_title": "Marketers",
    "use2_text": "Track competitor channels, analyze what content drives engagement and views.",
    "use3_title": "Data analysts",
    "use3_text": "Pull structured data for dashboards, ML training sets, or trend reports.",
    "use4_title": "Journalists",
    "use4_text": "Preserve evidence, search archives, build searchable databases of public messages.",

    # ===================== FAQ (on-page, long variants) =====================
    "faq_eyebrow": "FAQ",
    "faq_heading": "Frequently asked questions",
    "faq_q1": "Is this legal?",
    "faq_a1": "Yes. We only access public Telegram channels — the exact same data anyone with a Telegram account can already read. We don't break into private chats, bypass passwords, or hack anyone. We just put the data into a more usable format.",
    "faq_q2": "Do you store my exported file?",
    "faq_a2": "Only briefly. After your CSV is generated, it sits on our server for at most one hour and is then permanently deleted. Your download link stops working after that window. We don't keep any copy.",
    "faq_q3": "What's actually in the CSV?",
    "faq_a3": "Every message gets one row with: message ID, date/time (UTC), content (text or caption), view count, and a direct link back to the original message. Download it as <strong>CSV</strong> or <strong>Excel (.xlsx)</strong> — your choice. Media attachments are not downloaded — you'll see <code>[Media/File]</code> as the content for those.",
    "faq_q4": "What does \"public channel\" mean?",
    "faq_a4": "A channel that anyone can join or read without an invite. If you can see the channel's messages on the web at <code>t.me/channel_name</code> without logging in, it's public. Private channels (requiring an invite link or admin approval) cannot be exported.",
    "faq_q5": "Why USDT for payment?",
    "faq_a5": "USDT on the TRON network is fast (under a minute), cheap (often less than $0.10 in fees) and instantly verifiable on-chain. We're a small tool, not a Stripe-grade business — crypto lets us keep the price low without payment processor cuts.",
    "faq_q6": "My free limit isn't enough. Do I get a discount on Unlimited?",
    "faq_a6": "Unlimited is a flat one-time ${{ '%.2f' % paid_price }} for any channel — whatever its size, even millions of messages, the price is the same. No subscription, no surprise extras.",
    "faq_q7": "Can you export media (photos, videos)?",
    "faq_a7": "Not currently. The CSV contains text content, timestamps, view counts and links — but not the actual media files. We may add a media-zip option in the future; let us know if you need it.",
    "faq_q8": "How long does an unlimited export take?",
    "faq_a8": "Roughly 1,000 messages per 5 seconds on average. A 50,000-message channel takes about 4-5 minutes. Larger channels are slower because we rotate through multiple worker accounts to avoid rate limits.",
    "faq_q9": "Is there a limit on channel size?",
    "faq_a9": "No — there's no message cap. The Unlimited tier exports the <strong>whole channel</strong>, whatever its size, even hundreds of thousands of posts, for a flat ${{ '%.2f' % paid_price }}. Very large channels just take a little longer as we rotate through worker accounts. Got an unusually huge job? Email <a href=\"mailto:hello@telegramtocsv.com\">hello@telegramtocsv.com</a> and we'll help.",

    # ===================== CTA BAND =====================
    "cta_heading": "Ready to export?",
    "cta_text": "Paste a public Telegram channel link and have a clean CSV in your downloads folder in under a minute.",
    "cta_button": "Start free",

    # ===================== FOOTER (index) =====================
    "footer_tagline": "The simplest way to export public Telegram channels to a structured CSV or Excel file. No signup, no install, no fuss.",
    "footer_col_product": "Product",
    "footer_export_tool": "Export tool",
    "footer_col_company": "Company",
    "footer_about": "About",
    "footer_blog": "Blog",
    "footer_privacy_policy": "Privacy Policy",
    "footer_terms_of_service": "Terms of Service",
    "footer_contact": "Contact",
    "footer_copyright": "© 2026 TelegramtoCSV.com — All rights reserved.",
    "footer_disclaimer": "Not affiliated with Telegram Messenger Inc.",

    # ===================== COOKIE BANNER (index) =====================
    "cookie_aria": "Cookie consent",
    # split around the inline <a> link so the link text is its own key
    "cookie_text_pre": "We use cookies for essential site functionality and, on the free plan, to serve ads. By continuing to use the site you agree to our ",
    "cookie_text_post": ".",
    "cookie_privacy_link": "Privacy Policy",
    "cookie_decline": "Decline",
    "cookie_accept": "Accept all",
    # _legal_base / _blog_base use a shorter banner phrasing
    "cookie_text_short_pre": "We use cookies for essential site functionality and, on the free plan, to serve ads. By continuing you agree to our ",

    # ===================== SHARED CHROME: _legal_base =====================
    "legal_back_to_site": "Back to site",
    "legal_last_updated": "Last updated:",
    "ld_breadcrumb_home": "Home",
    # legal/blog footer short labels
    "footer_home": "Home",
    "footer_privacy_short": "Privacy",
    "footer_terms_short": "Terms",

    # ===================== SHARED CHROME: _blog_base =====================
    "blog_meta_updated": "Updated",
    "blog_min_read": "min read",
    "blog_cta_heading": "Want to try the tool yourself?",
    "blog_cta_text": "Export any public Telegram channel to CSV — free for the first 100 messages, $5 USDT for the unlimited archive.",
    "blog_cta_button": "Open TelegramtoCSV",
    "blog_all_posts": "All posts",
    "blog_questions": "Questions?",

    # ===================== blog/index.html =====================
    "blog_index_title": "Blog · TelegramtoCSV",
    "blog_index_description": "Guides, comparisons, and write-ups on exporting Telegram channels, data analysis, and OSINT research.",
    "blog_index_h1": "Blog",
    "blog_index_intro": "Guides on exporting Telegram channels, working with the data, and related topics for researchers, marketers, and analysts.",

    # ===================== JS-FACING (shipped via t_js|tojson) =====================
    "js_quote_uncapped": "This channel has ${n} messages → $${amt} USDT, one-time.",
    "js_quote_capped": "This channel has ${n} messages. We export the most recent ${Number(p.billable || 0).toLocaleString()} for $${amt} USDT — email us for the rest.",
    "js_pay_verified": "✓ Payment verified. Starting export…",
    "js_verify_failed": "Verification failed.",
    "js_network_error": "Network error. Try again.",
    "js_dl_xlsx": "Excel (.xlsx)",
    "js_dl_csv": "CSV",
    "js_dl_prefix": "Download ",
    "js_copied": "Copied!",
    "js_export_error": "Error: ",
    "js_txid_placeholder": "Paste your {NET} transaction ID (TXID)",
    "js_btn_export": "Export",
}


_RU = {
    # ===================== <head> / meta / SEO (index) =====================
    "meta_title": "TelegramtoCSV — экспорт telegram-канала в CSV и Excel",
    "meta_description": "Выгрузка сообщений из любого публичного telegram-канала в CSV или Excel (.xlsx) за секунды. Бесплатный фрагмент или весь архив за фиксированные $4 (разовая оплата). Без регистрации и установки программ.",
    "meta_keywords": "экспорт telegram канала в csv, парсер telegram каналов, скачать историю telegram канала, выгрузка сообщений из telegram, телеграм в эксель, telegram в csv, экспорт телеграм канала",
    "og_title": "TelegramtoCSV — экспорт telegram-каналов в CSV",
    "og_description": "Скачайте всю историю любого публичного telegram-канала в формате CSV или Excel. Быстро, безопасно, без регистрации.",

    # JSON-LD text (index)
    "ld_org_description": "Независимый сервис для экспорта истории публичных telegram-каналов в файлы CSV и Excel (.xlsx).",
    "ld_webapp_description": "Экспорт истории сообщений публичных telegram-каналов в готовый к скачиванию файл CSV или Excel (.xlsx). Бесплатно для первых {{ free_limit }} сообщений или весь архив за фиксированные ${{ '%.2f' % paid_price }} USDT (разовая оплата). Без регистрации и установки.",
    "ld_offer_free_name": "Бесплатный тариф",
    "ld_offer_free_description": "Последние {{ free_limit }} сообщений в одном экспорте, с рекламой, без регистрации.",
    "ld_offer_paid_name": "Без ограничений",
    "ld_offer_paid_description": "Полный архив канала, без рекламы, разовая оплата в USDT в сети TRC20 (TRON).",
    "ld_feature_list": "Экспорт в CSV и Excel (.xlsx) с ID сообщения, датой, текстом, числом просмотров и прямой ссылкой; бесплатный тариф без регистрации; автоудаление через 1 час; только публичные каналы; мгновенное скачивание прямо в браузере",

    # JSON-LD FAQPage (index) — short variants (from index_head unit)
    "ld_faq_q1": "Это законно?",
    "ld_faq_a1": "Да. Мы работаем только с публичными telegram-каналами — это ровно те же данные, которые может прочитать любой пользователь с аккаунтом в Telegram. Мы не взламываем приватные чаты, не обходим пароли и никого не хакаем. Мы просто приводим эти данные в более удобный формат.",
    "ld_faq_q2": "Вы храните мой экспортированный файл?",
    "ld_faq_a2": "Только недолго. После того как ваш CSV-файл сформирован, он хранится на нашем сервере не более одного часа, а затем безвозвратно удаляется. По истечении этого времени ссылка на скачивание перестаёт работать. Мы не оставляем себе никаких копий.",
    "ld_faq_q3": "Что именно содержится в CSV-файле?",
    "ld_faq_a3": "Каждому сообщению соответствует одна строка: ID сообщения, дата и время (UTC), содержимое (текст или подпись; [Media/File] для нетекстовых сообщений), число просмотров и прямая ссылка на оригинальное сообщение. Сами медиафайлы при этом не скачиваются.",
    "ld_faq_q4": "Что считается публичным каналом?",
    "ld_faq_a4": "Это канал, к которому любой может присоединиться или читать его без приглашения. Если сообщения канала видны в браузере по адресу t.me/channel_name без входа в аккаунт — значит, канал публичный. Приватные каналы (требующие пригласительной ссылки или одобрения администратора) экспортировать нельзя.",
    "ld_faq_q5": "Почему оплата в USDT?",
    "ld_faq_a5": "USDT в сети TRON — это быстро (меньше минуты), дёшево (часто менее $0,10 комиссии) и мгновенно проверяемо в блокчейне. Мы небольшой сервис, а не компания уровня Stripe, и криптовалюта позволяет держать цену низкой без отчислений платёжным провайдерам.",
    "ld_faq_q6": "Бесплатного лимита не хватает. Будет ли скидка на тариф «Без ограничений»?",
    "ld_faq_a6": "Тариф «Без ограничений» — это фиксированные ${{ '%.2f' % paid_price }} разово за любой канал, каким бы ни был его размер. Без подписки и скрытых доплат.",
    "ld_faq_q7": "Можно ли экспортировать медиа (фото, видео)?",
    "ld_faq_a7": "Пока нет. CSV содержит текст сообщений, отметки времени, число просмотров и ссылки, но не сами медиафайлы. В будущем мы, возможно, добавим выгрузку медиа в виде ZIP-архива.",
    "ld_faq_q8": "Сколько времени занимает экспорт без ограничений?",
    "ld_faq_a8": "В среднем около 1000 сообщений за 5 секунд. Канал на 50 000 сообщений обрабатывается примерно за 4–5 минут. Крупные каналы идут медленнее, потому что мы чередуем несколько рабочих аккаунтов, чтобы не упереться в лимиты Telegram.",
    "ld_faq_q9": "Есть ли ограничение на размер канала?",
    "ld_faq_a9": "Нет. Тариф «Без ограничений» выгружает весь канал любого размера — лимита на число сообщений нет, и это фиксированные ${{ '%.2f' % paid_price }} независимо от объёма. Очень крупные каналы просто обрабатываются чуть дольше.",

    # ===================== NAV (index) =====================
    "nav_features": "Возможности",
    "nav_how": "Как это работает",
    "nav_pricing": "Цены",
    "nav_faq": "FAQ",
    "nav_blog": "Блог",
    "nav_about": "О сервисе",
    "nav_export_now": "Начать экспорт",
    "aria_toggle_dark": "Переключить тёмную тему",

    # ===================== HERO =====================
    "hero_pill": "Без регистрации · Файлы удаляются через 1 час",
    "hero_h1": "Экспорт любого публичного Telegram-канала<br>в CSV или Excel",
    "hero_sub": "Скачайте всю историю сообщений публичного Telegram-канала — тексты, даты, просмотры и ссылки — за считаные секунды. Первые {{ free_limit }} сообщений бесплатно, или откройте полную историю за фиксированные ${{ '%.2f' % paid_price }} — любой канал, любой размер.",
    "hero_cta_primary": "Начать экспорт",
    "hero_cta_secondary": "Посмотреть цены",
    "trust_no_account": "Без аккаунта",
    "trust_autodelete": "Удаляется через 1 час",
    "trust_any_channel": "Работает с любым публичным каналом",

    # ===================== TOOL CARD =====================
    "tool_step1": "1 · Выберите тариф",
    "tier_free_name": "Бесплатно",
    "tier_free_price": "$0",
    "tier_free_desc": "Быстрый экспорт с рекламой · идеально для одного пробного образца",
    "tier_free_feat1": "Последние {{ free_limit }} сообщений",
    "tier_free_feat2": "CSV с просмотрами &amp; ссылками",
    "tier_free_feat3": "Без регистрации",
    "tier_free_feat4": "Автоудаление через 1 час",
    "tier_paid_name": "Безлимит",
    "badge_best": "ВЫГОДНО",
    "tier_paid_price": "${{ '%.2f' % paid_price }} <small>разово</small>",
    "tier_paid_desc": "Весь архив · фиксированная разовая цена · USDT",
    "tier_paid_feat1": "Вся история канала",
    "tier_paid_feat2": "Без лимита на число сообщений",
    "tier_paid_feat3": "Без рекламы",
    "tier_paid_feat4": "Приоритетная очередь обработки",
    "tool_step2": "2 · Вставьте ссылку на канал",
    "channel_placeholder": "https://t.me/channel_name",
    "btn_export": "Экспорт",
    "tool_step3": "3 · Выберите формат файла",
    "fmt_csv": "CSV <small>.csv</small>",
    "fmt_xlsx": "Excel <small>.xlsx</small>",

    # Progress
    "progress_processing": "Обработка",
    "progress_connecting": "Подключение…",

    # Payment widget
    "pay_head": "Требуется оплата",
    "net_trc20": "TRON · TRC20",
    "net_trc20_tag": "дешевле всего",
    "net_bep20": "BSC · BEP20",
    "net_bep20_tag": "низкая комиссия",
    "net_erc20": "Ethereum · ERC20",
    "net_erc20_tag": "высокий газ",
    "pay_gas_warn": "⚠ Комиссия сети Ethereum (её платите вы) обычно составляет $1–5+ — нередко больше самого экспорта. Используйте <strong>TRON</strong> или <strong>BSC</strong>, чтобы платить значительно меньше.",
    "pay_sub": "Отправьте <strong><span id=\"paySendAmt\">{{ '%.2f' % paid_price }}</span> USDT</strong> в сети <strong><span id=\"payNetName\">TRON (TRC20)</span></strong>\n                    на кошелёк ниже. Отсканируйте QR в приложении криптокошелька или скопируйте адрес вручную.",
    "pay_qr_label": "Сканируйте для оплаты",
    "pay_qr_alt": "QR-код кошелька USDT",
    "pay_qr_hint": "Откройте <strong>Trust Wallet</strong>, <strong>Binance</strong>, <strong>Bybit</strong>\n                        или любой кошелёк с поддержкой USDT, выберите USDT в выбранной сети, отсканируйте этот код и укажите сумму\n                        <strong><span id=\"payScanAmt\">{{ '%.2f' % paid_price }}</span> USDT</strong>.",
    "pay_amount_label": "Сумма",
    "pay_wallet_label_pre": "Кошелёк (",
    "pay_wallet_label_post": ")",
    "btn_copy": "Копировать",
    "btn_verify": "Проверить",

    # Download block
    "download_complete": "Экспорт завершён",
    "download_ready": "Ваш файл готов. Ссылка действует 1 час.",
    "download_file": "Скачать файл",

    # ===================== FEATURES =====================
    "features_eyebrow": "Возможности",
    "features_heading": "Всё, что нужно для архивации канала",
    "features_intro": "Создано для исследователей, маркетологов и аналитиков, которым нужны чистые структурированные данные, а не скриншоты.",
    "feat1_title": "Структурированный CSV на выходе",
    "feat1_text": "Каждое сообщение — отдельная строка с ID, датой, текстом, числом просмотров и прямой ссылкой. Выгрузка в CSV или Excel (.xlsx) — открывается в Excel, Google Таблицах, pandas, где угодно.",
    "feat2_title": "Полная история, а не только последние посты",
    "feat2_text": "Большинство сервисов ограничиваются парой сотен сообщений. На тарифе «Безлимит» мы выгружаем весь архив — даже каналы со 100 000+ постов.",
    "feat3_title": "Быстро и без блокировок по лимитам",
    "feat3_text": "Работа распределяется между множеством рабочих аккаунтов, чтобы обойти флуд-лимиты Telegram. Канал на 10 000 сообщений выгружается меньше чем за минуту.",
    "feat4_title": "Приватность по умолчанию",
    "feat4_text": "Без регистрации, без e-mail, без отслеживающих cookie. Готовый файл автоматически удаляется с наших серверов через час.",
    "feat5_title": "Прямо в браузере, без установки",
    "feat5_text": "Работает в любом современном браузере на компьютере и телефоне. Ничего не нужно устанавливать, настраивать Python-скрипты или возиться с API-ключами.",
    "feat6_title": "Только публичные каналы",
    "feat6_text": "Мы работаем только с общедоступным контентом — теми же данными, которые любой может увидеть в приложении Telegram. Никаких личных переписок и закрытых каналов.",

    # ===================== HOW IT WORKS =====================
    "how_eyebrow": "Как это работает",
    "how_heading": "Три шага, меньше минуты",
    "step1_title": "Вставьте ссылку на канал",
    "step1_text": "Скопируйте ссылку на публичный Telegram-канал (вида <code>t.me/channel_name</code>) и вставьте её в поле экспорта вверху страницы.",
    "step2_title": "Выберите бесплатный или безлимит",
    "step2_text": "Бесплатный тариф охватывает последние {{ free_limit }} сообщений — то, что нужно для быстрого ознакомления. Тариф «Безлимит» выгружает всю историю за фиксированные ${{ '%.2f' % paid_price }} в USDT — одна оплата, канал любого размера.",
    "step3_title": "Скачайте свой CSV",
    "step3_text": "Мы собираем данные и отдаём файл в формате CSV или Excel (.xlsx). Откройте его в Excel, Google Таблицах, Notion или загрузите в любой удобный инструмент анализа.",

    # ===================== PRICING =====================
    "pricing_eyebrow": "Цены",
    "pricing_heading": "Простые и прозрачные цены",
    "pricing_intro": "Сначала попробуйте бесплатно. Переходите на платный тариф, только когда понадобится полный архив.",
    "price_free_title": "Бесплатно",
    "price_free_price": "$0",
    "price_free_sub": "Навсегда · с рекламой",
    "price_free_feat1": "Последние {{ free_limit }} сообщений",
    "price_free_feat2": "Экспорт в CSV с просмотрами и ссылками",
    "price_free_feat3": "Без регистрации",
    "price_free_feat4": "Удаление через 1 час",
    "price_free_feat5": "Не более 100 экспортов в день с одного IP",
    "price_free_cta": "Начать бесплатно",
    "price_paid_title": "Безлимит",
    "price_paid_price": "${{ '%.2f' % paid_price }}",
    "price_paid_sub": "Разовая оплата · канал любого размера",
    "price_paid_feat1": "Вся история канала*",
    "price_paid_feat2": "Без рекламы",
    "price_paid_feat3": "Оплата в USDT (TRC20)",
    "price_paid_feat4": "Тот же формат CSV, но полностью целиком",
    "price_paid_feat5": "Приоритетная очередь обработки",
    "price_paid_cta": "Выбрать «Безлимит»",
    "price_paid_footnote": "* Фиксированные ${{ '%.2f' % paid_price }} за любой канал любого размера — без поштучной оплаты и без лимита. Формат на выбор — <a href=\"#faq\" style=\"color: var(--muted-2); text-decoration: underline;\">CSV или Excel</a>.",

    # ===================== USE CASES (added in-style) =====================
    "uses_eyebrow": "Сценарии использования",
    "uses_heading": "Кто экспортирует данные Telegram?",
    "use1_title": "Исследователи",
    "use1_text": "Анализ тональности, восстановление хронологии, длительные исследования публичного дискурса.",
    "use2_title": "Маркетологи",
    "use2_text": "Отслеживайте каналы конкурентов, анализируйте, какой контент даёт вовлечённость и просмотры.",
    "use3_title": "Аналитики данных",
    "use3_text": "Выгружайте структурированные данные для дашбордов, обучающих выборок ML или отчётов о трендах.",
    "use4_title": "Журналисты",
    "use4_text": "Сохраняйте доказательства, ищите по архивам, стройте базы данных публичных сообщений с поиском.",

    # ===================== FAQ (on-page, long variants) =====================
    "faq_eyebrow": "FAQ",
    "faq_heading": "Часто задаваемые вопросы",
    "faq_q1": "Это законно?",
    "faq_a1": "Да. Мы работаем только с публичными Telegram-каналами — теми же данными, которые и так может прочитать любой пользователь с аккаунтом Telegram. Мы не взламываем личные переписки, не обходим пароли и никого не «ломаем». Мы лишь приводим данные к удобному формату.",
    "faq_q2": "Вы храните мой выгруженный файл?",
    "faq_a2": "Только короткое время. После создания CSV файл лежит на нашем сервере максимум один час, а затем безвозвратно удаляется. По истечении этого срока ссылка на скачивание перестаёт работать. Никаких копий мы не храним.",
    "faq_q3": "Что именно содержится в CSV?",
    "faq_a3": "Каждое сообщение — одна строка: ID сообщения, дата и время (UTC), содержимое (текст или подпись), число просмотров и прямая ссылка на оригинальное сообщение. Скачать можно в <strong>CSV</strong> или <strong>Excel (.xlsx)</strong> — на ваш выбор. Медиафайлы не скачиваются — вместо них в содержимом будет указано <code>[Media/File]</code>.",
    "faq_q4": "Что значит «публичный канал»?",
    "faq_a4": "Это канал, на который любой может подписаться или читать его без приглашения. Если сообщения канала видны в браузере по адресу <code>t.me/channel_name</code> без входа в аккаунт — он публичный. Закрытые каналы (требующие ссылку-приглашение или одобрение администратора) выгрузить нельзя.",
    "faq_q5": "Почему оплата в USDT?",
    "faq_a5": "USDT в сети TRON — это быстро (меньше минуты), дёшево (комиссия часто менее $0,10) и мгновенно проверяется в блокчейне. Мы небольшой сервис, а не компания уровня Stripe — криптовалюта позволяет держать цену низкой без отчислений платёжным провайдерам.",
    "faq_q6": "Бесплатного лимита не хватает. Будет ли скидка на «Безлимит»?",
    "faq_a6": "«Безлимит» — это фиксированные ${{ '%.2f' % paid_price }} разово за любой канал: каким бы ни был его размер, хоть миллионы сообщений, цена одна и та же. Никакой подписки и скрытых доплат.",
    "faq_q7": "Можно ли выгружать медиа (фото, видео)?",
    "faq_a7": "Пока нет. В CSV попадают тексты, даты, число просмотров и ссылки — но не сами медиафайлы. Возможно, в будущем мы добавим выгрузку медиа в zip-архиве; напишите нам, если вам это нужно.",
    "faq_q8": "Сколько времени занимает безлимитный экспорт?",
    "faq_a8": "В среднем около 1 000 сообщений за 5 секунд. Канал на 50 000 сообщений выгружается примерно за 4–5 минут. Крупные каналы идут медленнее, потому что мы чередуем несколько рабочих аккаунтов, чтобы не упереться в лимиты.",
    "faq_q9": "Есть ли ограничение по размеру канала?",
    "faq_a9": "Нет — лимита на количество сообщений нет. Тариф «Безлимит» выгружает <strong>весь канал</strong> любого размера, даже на сотни тысяч постов, за фиксированные ${{ '%.2f' % paid_price }}. Очень крупные каналы просто обрабатываются чуть дольше, пока мы чередуем рабочие аккаунты. Нестандартно большой объём? Напишите на <a href=\"mailto:hello@telegramtocsv.com\">hello@telegramtocsv.com</a>, и мы поможем.",

    # ===================== CTA BAND =====================
    "cta_heading": "Готовы к экспорту?",
    "cta_text": "Вставьте ссылку на публичный Telegram-канал — и меньше чем за минуту чистый CSV окажется в папке загрузок.",
    "cta_button": "Начать бесплатно",

    # ===================== FOOTER (index) =====================
    "footer_tagline": "Самый простой способ выгрузить публичные Telegram-каналы в структурированный файл CSV или Excel. Без регистрации, без установки, без лишних хлопот.",
    "footer_col_product": "Продукт",
    "footer_export_tool": "Инструмент экспорта",
    "footer_col_company": "О сервисе",
    "footer_about": "О нас",
    "footer_blog": "Блог",
    "footer_privacy_policy": "Политика конфиденциальности",
    "footer_terms_of_service": "Условия использования",
    "footer_contact": "Контакты",
    "footer_copyright": "© 2026 TelegramtoCSV.com — Все права защищены.",
    "footer_disclaimer": "Не связано с Telegram Messenger Inc.",

    # ===================== COOKIE BANNER (index) =====================
    "cookie_aria": "Согласие на использование cookie",
    "cookie_text_pre": "Мы используем cookie для базовой работы сайта, а на бесплатном тарифе — для показа рекламы. Продолжая пользоваться сайтом, вы соглашаетесь с нашей ",
    "cookie_text_post": ".",
    "cookie_privacy_link": "Политикой конфиденциальности",
    "cookie_decline": "Отклонить",
    "cookie_accept": "Принять все",
    "cookie_text_short_pre": "Мы используем cookie для базовой работы сайта, а на бесплатном тарифе — для показа рекламы. Продолжая пользоваться сайтом, вы соглашаетесь с нашей ",

    # ===================== SHARED CHROME: _legal_base =====================
    "legal_back_to_site": "Назад на сайт",
    "legal_last_updated": "Последнее обновление:",
    "ld_breadcrumb_home": "Главная",
    "footer_home": "Главная",
    "footer_privacy_short": "Конфиденциальность",
    "footer_terms_short": "Условия",

    # ===================== SHARED CHROME: _blog_base =====================
    "blog_meta_updated": "Обновлено",
    "blog_min_read": "мин чтения",
    "blog_cta_heading": "Хотите попробовать сервис сами?",
    "blog_cta_text": "Экспорт любого публичного Telegram-канала в CSV — первые 100 сообщений бесплатно, полный архив за $5 USDT.",
    "blog_cta_button": "Открыть TelegramtoCSV",
    "blog_all_posts": "Все статьи",
    "blog_questions": "Остались вопросы?",

    # ===================== blog/index.html =====================
    "blog_index_title": "Блог · TelegramtoCSV — парсер Telegram-каналов и экспорт в CSV",
    "blog_index_description": "Гайды, сравнения и разборы по экспорту Telegram-каналов в CSV, выгрузке сообщений из Telegram и OSINT-исследованиям.",
    "blog_index_h1": "Блог",
    "blog_index_intro": "Гайды по экспорту Telegram-каналов в CSV и Excel, работе с выгруженными данными и смежным темам — для исследователей, маркетологов и аналитиков.",

    # ===================== JS-FACING (shipped via t_js|tojson) =====================
    "js_quote_uncapped": "В этом канале ${n} сообщений → $${amt} USDT, разовый платёж.",
    "js_quote_capped": "В этом канале ${n} сообщений. Мы выгрузим последние ${Number(p.billable || 0).toLocaleString()} за $${amt} USDT — напишите нам, чтобы получить остальные.",
    "js_pay_verified": "✓ Оплата подтверждена. Запускаем экспорт…",
    "js_verify_failed": "Не удалось подтвердить платёж.",
    "js_network_error": "Ошибка сети. Попробуйте ещё раз.",
    "js_dl_xlsx": "Excel (.xlsx)",
    "js_dl_csv": "CSV",
    "js_dl_prefix": "Скачать ",
    "js_copied": "Скопировано!",
    "js_export_error": "Ошибка: ",
    "js_txid_placeholder": "Вставьте ID транзакции {NET} (TXID)",
    "js_btn_export": "Экспорт",
}


STRINGS = {"en": _EN, "ru": _RU}


def js_dict(lang):
    """Small dict of JUST the JS-facing keys for `const T = {{ t_js|tojson }};`."""
    t = STRINGS.get(lang, STRINGS["en"])
    return {k: t[k] for k in JS_KEYS}


# Fail fast at import time if the two languages ever drift out of key-sync.
assert set(_EN) == set(_RU), (
    "translations.py: EN/RU key sets differ: "
    f"{set(_EN) ^ set(_RU)}"
)
