import os
from flask import Flask, request, redirect, session, abort
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

import dmapiclient
from dmutils import init_app
from dmutils.user import User
from dmutils.external import external as external_blueprint
from govuk_frontend_jinja.flask_ext import init_govuk_frontend

from config import configs


login_manager = LoginManager()
data_api_client = dmapiclient.DataAPIClient()
csrf = CSRFProtect()


def create_app(config_name):
    application = Flask(__name__,
                        static_folder='static/',
                        static_url_path=configs[config_name].STATIC_URL_PATH)

    # allow using govuk-frontend Nunjucks templates
    init_govuk_frontend(application)

    init_app(
        application,
        configs[config_name],
        data_api_client=data_api_client,
        login_manager=login_manager,
    )

    from .metrics import metrics as metrics_blueprint, gds_metrics
    from .main import main as main_blueprint
    from .healthcheck import healthcheck as healthcheck_blueprint

    application.register_blueprint(metrics_blueprint, url_prefix='/user')
    application.register_blueprint(main_blueprint, url_prefix='/user')
    application.register_blueprint(healthcheck_blueprint, url_prefix='/healthcheck')

    # Must be registered last so that any routes declared in the app are registered first (i.e. take precedence over
    # the external NotImplemented routes in the dm-utils external blueprint).
    application.register_blueprint(external_blueprint)

    # In native AWS we need to stipulate the absolute login URL as per:
    # https://flask-login.readthedocs.io/en/latest/#flask_login.LoginManager.login_view
    login_manager.login_view = os.getenv('DM_LOGIN_URL', 'main.render_login')
    login_manager.login_message = None  # don't flash message to user
    gds_metrics.init_app(application)
    csrf.init_app(application)

    @application.before_request
    def remove_trailing_slash():
        if request.path != '/' and request.path.endswith('/'):
            if request.query_string:
                return redirect(
                    '{}?{}'.format(
                        request.path[:-1],
                        request.query_string.decode('utf-8')
                    ),
                    code=301
                )
            else:
                return redirect(request.path[:-1], code=301)

    @application.before_request
    def refresh_session():
        session.permanent = True
        session.modified = True

    return application


@login_manager.user_loader
def load_user(user_id):
    return User.load_user(data_api_client, user_id)
