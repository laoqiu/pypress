#!/usr/bin/env python
#coding=utf-8

"""
    forms: account.py
    ~~~~~~~~~~~~~

    :license: BSD, see LICENSE for more details.
"""
from flaskext.wtf import Form, TextAreaField, HiddenField, BooleanField, \
        PasswordField, SubmitField, TextField, ValidationError, \
        required, email, equal_to, regexp

from flaskext.babel import gettext, lazy_gettext as _ 

from pypress.extensions import db
from pypress.models import User

from .validators import is_username

class LoginForm(Form):

    login = TextField(_("Username or email address"), validators=[
                      required(message=\
                               _("You must provide an email or username"))])

    password = PasswordField(_("Password"))

    remember = BooleanField(_("Remember me"))

    next = HiddenField()

    submit = SubmitField(_("Login"))


class SignupForm(Form):

    username = TextField(_("Username"), validators=[
                         required(message=_("Username required")), 
                         is_username])

    nickname = TextField(_("Nickname"), validators=[
                         required(message=_("Nickname required"))])

    password = PasswordField(_("Password"), validators=[
                             required(message=_("Password required"))])

    password_again = PasswordField(_("Password again"), validators=[
                                   equal_to("password", message=\
                                            _("Passwords don't match"))])

    email = TextField(_("Email address"), validators=[
                      required(message=_("Email address required")), 
                      email(message=_("A valid email address is required"))])

    code = TextField(_("Signup Code"))

    next = HiddenField()

    submit = SubmitField(_("Signup"))

    def validate_username(self, field):
        user = User.query.filter(User.username.like(field.data)).first()
        if user:
            raise ValidationError, gettext("This username is taken")

    def validate_email(self, field):
        user = User.query.filter(User.email.like(field.data)).first()
        if user:
            raise ValidationError, gettext("This email is taken")


class RecoverPasswordForm(Form):

    email = TextField("Your email address", validators=[
                      email(message=_("A valid email address is required"))])

    submit = SubmitField(_("Find password"))


class ChangePasswordForm(Form):

    password_old = PasswordField(_("Password"), validators=[
                             required(message=_("Password is required"))])

    password = PasswordField(_("New Password"), validators=[
                             required(message=_("New Password is required"))])
    
    password_again = PasswordField(_("Password again"), validators=[
                                   equal_to("password", message=\
                                            _("Passwords don't match"))])

    submit = SubmitField(_("Save"))


class DeleteAccountForm(Form):
    
    recaptcha = TextField(_("Recaptcha"))

    submit = SubmitField(_("Delete"))


class TwitterForm(Form):

    content = TextAreaField(_("Content"), validators=[
                        required(message=_("Content is required"))])

    submit = SubmitField(_("Send"))

