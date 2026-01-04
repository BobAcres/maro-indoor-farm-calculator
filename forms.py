from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, SelectField, FloatField, SubmitField
from wtforms.validators import Optional

class MyForm(FlaskForm):
    country = SelectField("Country", choices=[], validators=[Optional()])
    currency_override = StringField("Currency override", validators=[Optional()])

    area_m2 = FloatField("Area (m²)", validators=[Optional()])
    system_type = SelectField(...)
    crop = SelectField(...)
    setup_level = SelectField(...)

    annual_production_cost = FloatField(validators=[Optional()])
    price_per_unit = FloatField(validators=[Optional()])
    capex_per_m2 = FloatField(validators=[Optional()])

    use_solar = BooleanField("Use solar")
    submit = SubmitField("Calculate")