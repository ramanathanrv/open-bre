from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from . import db  # import the shared db instance

class BaseModel(db.Model):
    __abstract__ = True  # SQLAlchemy won’t create a table for this

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    def save(self):
        """Convenience helper to save the model."""
        db.session.add(self)
        db.session.commit()

    def delete(self):
        """Convenience helper to delete the model."""
        db.session.delete(self)
        db.session.commit()
