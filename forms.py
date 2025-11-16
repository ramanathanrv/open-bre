# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length
from models.credit_policy import StatusEnum

class CreditPolicyForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=50)])
    version = IntegerField('Version', validators=[DataRequired()])
    status = SelectField(
        'Status',
        choices=[(status.name, status.value) for status in StatusEnum],
        default='DRAFT'
    )
    policyJSON = TextAreaField('Policy JSON')
    submit = SubmitField('Save')
