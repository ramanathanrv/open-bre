from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import models so they register with SQLAlchemy
from .credit_policy import CreditPolicy

# Import event listeners last (after models)
from . import events