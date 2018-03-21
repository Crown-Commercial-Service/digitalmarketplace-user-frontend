# coding: utf-8
from flask_login import (current_user, login_required)
from flask import (
    flash,
    render_template,
    request,
    url_for
)
from .. import main
from ..forms.user_research import UserResearchOptInForm
from ... import data_api_client


@main.route('/notifications/user-research', methods=["GET", "POST"])
@login_required
def user_research_consent():

    form = UserResearchOptInForm(request.form)
    status_code = 200
    errors = {}

    if request.method == "POST":
        if form.validate_on_submit():
            user_research_opt_in = form.data.get('user_research_opt_in')
            data_api_client.update_user(
                current_user.id,
                user_research_opted_in=user_research_opt_in,
                updater=current_user.email_address
            )

            flash("Your preference has been saved", 'success')
        else:
            status_code = 400
            errors = {
                key: {'question': form[key].label.text, 'input_name': key, 'message': form[key].errors[0]}
                for key, value in form.errors.items()
            }
    else:
        user = data_api_client.get_user(current_user.id)
        form = UserResearchOptInForm(user_research_opt_in=user['users']['userResearchOptedIn'])

    if current_user.role == 'supplier':
        dashboard_url = url_for('external.supplier_dashboard')
    else:
        dashboard_url = url_for('external.buyer_dashboard')

    additional_headers = []
    cookie_name = 'seen_user_research_message'

    if cookie_name not in request.cookies:
        additional_headers = {'Set-Cookie': "{}=yes; Path=/".format(cookie_name)}

    return render_template(
        "notifications/user-research-consent.html",
        form=form,
        errors=errors,
        dashboard_url=dashboard_url
    ), status_code, additional_headers
