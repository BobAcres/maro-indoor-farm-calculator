from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, FloatField, SubmitField
from wtforms.validators import Optional

class MyForm(FlaskForm):
    country = SelectField("Country", choices=[], validators=[Optional()])
    area_m2 = FloatField("Area (m²)", validators=[Optional()])
    system_type = SelectField(
        "System Type",
        choices=[
            ("soil", "Soil"),
            ("hydroponic", "Hydroponic"),
        ],
        default="soil",
    )
    crop = StringField("Crop", validators=[Optional()])
    annual_production_cost = FloatField("Annual Production Cost", validators=[Optional()])
    labor_cost = FloatField("Labor Cost", validators=[Optional()])
    submit = SubmitField("Calculate")