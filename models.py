from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(
        db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )
    channel_link = db.Column(db.String(255), nullable=False)

    # Hybrid model: "free" = limited messages, ad-supported; "paid" = unlimited
    tier = db.Column(db.String(20), nullable=False, default="free")

    # Payment fields (only populated for paid orders)
    currency = db.Column(db.String(10), default="USDT")
    # Which USDT network the order was paid on: TRC20 | ERC20 | BEP20
    network = db.Column(db.String(10), nullable=False, default="TRC20")
    amount = db.Column(db.Float, nullable=True)
    txid = db.Column(db.String(100), unique=True, nullable=True)
    payment_verified = db.Column(db.Boolean, default=False)
    payment_verified_at = db.Column(db.DateTime, nullable=True)

    # Tracking
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    worker_used = db.Column(db.String(50), nullable=True)
    message_count = db.Column(db.Integer, default=0)
    # Total messages in the channel (may exceed message_count if hit paid cap)
    total_messages = db.Column(db.Integer, default=0)

    # State machine: queued, awaiting_payment, processing, completed, failed
    status = db.Column(db.String(30), default="queued")
    progress = db.Column(db.Integer, default=0)
    status_message = db.Column(db.String(255), default="Waiting...")

    file_path = db.Column(db.String(500), nullable=True)
    file_format = db.Column(db.String(10), default="csv")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "token": self.token,
            "channel": self.channel_link,
            "tier": self.tier,
            "currency": self.currency,
            "network": self.network,
            "amount": self.amount,
            "txid": self.txid,
            "payment_verified": self.payment_verified,
            "status": self.status,
            "progress": self.progress,
            "status_message": self.status_message,
            "worker_used": self.worker_used,
            "message_count": self.message_count,
            "total_messages": self.total_messages,
            "file_format": self.file_format,
            "ip_address": self.ip_address,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "completed_at": self.completed_at.strftime("%Y-%m-%d %H:%M:%S") if self.completed_at else None,
        }
