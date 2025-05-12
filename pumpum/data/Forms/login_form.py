from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.fields import EmailField
from wtforms.validators import DataRequired, Length, Email


# Форма для Flask0
class LoginForm(FlaskForm):
    username = StringField('Логин', validators=[
        DataRequired(message="Поле обязательно")
    ])

    password = PasswordField('Пароль', validators=[
        DataRequired(message="Поле обязательно")
    ])

    submit = SubmitField('Войти')
