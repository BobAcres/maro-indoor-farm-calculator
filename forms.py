from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    SelectField,
    FloatField,
    BooleanField,
    SubmitField
)
from wtforms.validators import Optional, NumberRange, Length


class MyForm(FlaskForm):
    # Location & setup
    country = SelectField("Country", choices=[], validators=[Optional()])
    setup_level = SelectField("Setup level", choices=[], validators=[Optional()])
    system_type = SelectField("System type", choices=[], validators=[Optional()])
    crop = SelectField("Crop", choices=[], validators=[Optional()])
    currency_override = StringField(
        "Currency override",
        validators=[Optional(), Length(max=15)],
    )

    # Area
    area_m2 = FloatField(
        "Greenhouse area (m²)",
        validators=[Optional(), NumberRange(min=0)],
        default=None,
    )

    # Economics — USER OVERRIDES
    annual_production_cost = FloatField(
        "Annual production cost (optional)",
        validators=[Optional(), NumberRange(min=0)],
        default=None,
    )

    price_per_unit = FloatField(
        "Market price per kg (optional)",
        validators=[Optional(), NumberRange(min=0)],
        default=None,
    )

    capex_per_m2 = FloatField(
        "Capital cost per m² (optional)",
        validators=[Optional(), NumberRange(min=0)],
        default=None,
    )

    # Energy
    use_solar = BooleanField("Use solar power")

    submit = SubmitField("Calculate")