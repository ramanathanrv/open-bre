from datetime import datetime
from .base import db, BaseModel
import enum

class StatusEnum(enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class CreditPolicy(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    policyJSON = db.Column(db.Text, nullable=True)
    policyJSON_d3 = db.Column(db.Text, nullable=True)
    status = db.Column(db.Enum(StatusEnum), nullable=False, default=StatusEnum.DRAFT)
    version = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"<CreditPolicy {self.name}>"
