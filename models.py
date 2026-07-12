# models.py — Database models for ScopeCreep
# Uses SQLAlchemy (ORM) with SQLite for local dev.
# SQLite = a single file (scopecreep.db) on disk, no server needed.

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class User(db.Model, UserMixin):
    """A ScopeCreep user account."""
    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    change_orders = db.relationship("ChangeOrder", backref="user", lazy=True)

    def __repr__(self):
        return f"<User {self.email}>"


class ChangeOrder(db.Model):
    """A single change order record."""
    id                = db.Column(db.Integer, primary_key=True)
    user_id           = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    client_name       = db.Column(db.String(100))
    client_email      = db.Column(db.String(120))
    scope_item        = db.Column(db.Text)
    total             = db.Column(db.Float)
    filename          = db.Column(db.String(200))
    payment_link      = db.Column(db.String(500))
    status            = db.Column(db.String(20), default="pending")
    created_at        = db.Column(db.DateTime, default=datetime.utcnow)
    status_updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert to dict so templates don't need to change much."""
        return {
            "id":                self.id,
            "client_name":       self.client_name,
            "client_email":      self.client_email,
            "scope_item":        self.scope_item,
            "total":             self.total,
            "filename":          self.filename,
            "payment_link":      self.payment_link,
            "status":            self.status,
            "created_at":        self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else "",
            "status_updated_at": self.status_updated_at.strftime("%Y-%m-%d %H:%M") if self.status_updated_at else "",
        }
