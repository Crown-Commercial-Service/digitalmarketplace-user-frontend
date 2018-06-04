from flask import current_app
from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import PasswordField
from wtforms.validators import DataRequired, EqualTo, Length, Regexp, ValidationError

from dmutils.email.helpers import hash_string
from dmutils.forms import StripWhitespaceStringField, StringField

from app import data_api_client


EMAIL_LOGIN_HINT = "Enter the email address you used to register with the Digital Marketplace"
PASSWORD_HINT = "Must be between 10 and 50 characters"
PHONE_NUMBER_HINT = "If there are any urgent problems with your requirements, we need your phone number so the " \
                    "support team can help you fix them quickly."


class LoginForm(FlaskForm):
    email_address = StripWhitespaceStringField(
        'Email address', id="input_email_address",
        validators=[
            DataRequired(message="You must provide an email address"),
            Regexp("^[^@^\s]+@[^@^\.^\s]+(\.[^@^\.^\s]+)+$",
                   message="You must provide a valid email address")
        ]
    )
    password = PasswordField(
        'Password', id="input_password",
        validators=[
            DataRequired(message="You must provide your password")
        ]
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.email_address.hint = EMAIL_LOGIN_HINT


class EmailAddressForm(FlaskForm):
    email_address = StripWhitespaceStringField(
        'Email address', id="input_email_address",
        validators=[
            DataRequired(message="You must provide an email address"),
            Regexp("^[^@^\s]+@[^@^\.^\s]+(\.[^@^\.^\s]+)+$",
                   message="You must provide a valid email address")
        ]
    )


class MatchesCurrentPassword:
    def __init__(self, message):
        self.message = message

    def __call__(self, form, field):
        user_json = data_api_client.authenticate_user(current_user.email_address, field.data)

        if user_json is None:
            current_app.logger.info("change_password.fail: failed to authenticate user {email_hash}",
                                    extra={'email_hash': hash_string(current_user.email_address)})

            raise ValidationError(self.message)


class PasswordChangeForm(FlaskForm):
    old_password = PasswordField(
        'Old password', id="input_old_password",
        validators=[
            DataRequired(message="You must enter your old password"),
            MatchesCurrentPassword(message="Make sure you’ve entered the right password."),
        ]
    )
    password = PasswordField(
        'New password', id="input_password",
        validators=[
            DataRequired(message="You must enter a new password"),
            Length(min=10,
                   max=50,
                   message="Passwords must be between 10 and 50 characters"
                   )
        ]
    )
    confirm_password = PasswordField(
        'Confirm new password', id="input_confirm_password",
        validators=[
            DataRequired(message="Please confirm your new password"),
            EqualTo('password', message="The passwords you entered do not match")
        ]
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.password.hint = PASSWORD_HINT


class PasswordResetForm(PasswordChangeForm):
    """
    Subclasses PasswordChangeForm so we can keep validation/password policy in one place
    'Old password' not required for PasswordReset (as the user likely doesn't know it)
    """
    old_password = None


class CreateUserForm(FlaskForm):
    name = StripWhitespaceStringField(
        'Your name', id="input_name",
        validators=[
            DataRequired(message="You must enter a name"),
            Length(min=1,
                   max=255,
                   message="Names must be between 1 and 255 characters"
                   )
        ]
    )

    phone_number = StringField(
        'Phone number', id="input_phone_number",
        validators=[
            Regexp("^$|^\\+?([\\d\\s()-]){9,20}$",
                   message=("Phone numbers must be at least 9 characters long. "
                            "They can only include digits, spaces, plus and minus signs, and brackets.")
                   )
        ]
    )

    password = PasswordField(
        'Password', id="input_password",
        validators=[
            DataRequired(message="You must enter a password"),
            Length(min=10,
                   max=50,
                   message="Passwords must be between 10 and 50 characters"
                   )
        ]
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.phone_number.hint = PHONE_NUMBER_HINT
        self.password.hint = PASSWORD_HINT
