from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.fields.simple import EmailField
from wtforms.validators import DataRequired, Length, Email


class RegistrationForm(FlaskForm):
    username = StringField('Логин', validators=[
        DataRequired(message="Поле обязательно"),
        Length(min=4, max=20, message="Логин должен быть от 4 до 20 символов")
    ])

    password = PasswordField('Пароль', validators=[
        DataRequired(message="Поле обязательно"),
        Length(min=6, message="Пароль должен быть не менее 6 символов")
    ])

    email = EmailField('Почта', validators=[
        DataRequired(message="Поле обязательно"),
        Email(message="Некорректный email")
    ])

    full_name = StringField('ФИО', validators=[
        DataRequired(message="Поле обязательно"),
        Length(min=5, message="Введите полное имя")
    ])

    submit = SubmitField('Зарегистрироваться')