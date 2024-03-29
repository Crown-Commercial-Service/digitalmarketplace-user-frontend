# coding: utf-8
from dmutils.email import generate_token
from ...helpers import BaseApplicationTest
from lxml import html
import mock

from app.main.forms.auth_forms import (
    EMAIL_EMPTY_ERROR_MESSAGE,
    EMAIL_INVALID_ERROR_MESSAGE,
    LOGIN_PASSWORD_EMPTY_ERROR_MESSAGE
)
from app.main.views.auth import NO_ACCOUNT_MESSAGE


# subset of WCAG 2.1 input purposes
# https://www.w3.org/TR/WCAG21/#input-purposes
VALID_INPUT_PURPOSES = {
    "username",
    "current-password",
    "new-password",
}


class TestLogin(BaseApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.auth.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()
        self.data_api_client.authenticate_user.return_value = self.user(
            123, "email@email.com", 1234, 'name', 'name'  # supplier user
        )

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_should_show_login_page(self):
        res = self.client.get("/user/login")
        assert res.status_code == 200
        assert "Log in to the Digital Marketplace" in res.get_data(as_text=True)

    @mock.patch('app.main.views.auth.are_new_frameworks_live')
    def test_should_hide_banner_when_not_needed(self, are_new_frameworks_live):
        are_new_frameworks_live.return_value = False
        res = self.client.get("/user/login")
        assert res.status_code == 200
        are_new_frameworks_live.assert_called_once()
        assert "Important information" not in res.get_data(as_text=True)

    @mock.patch('app.main.views.auth.are_new_frameworks_live')
    def test_should_show_banner_when_needed(self, are_new_frameworks_live):
        are_new_frameworks_live.return_value = True
        res = self.client.get("/user/login")
        assert res.status_code == 200
        assert "Important information" in res.get_data(as_text=True)

    @mock.patch('app.main.views.auth.are_new_frameworks_live')
    def test_should_pass_through_request_parameters(self, are_new_frameworks_live):
        self.client.get("/user/login?show_dmp_so_banner=true")
        assert are_new_frameworks_live.call_args[0][0].to_dict() == {"show_dmp_so_banner": 'true'}

    def test_should_redirect_to_supplier_dashboard_on_supplier_login(self):
        res = self.client.post("/user/login", data={
            'email_address': 'valid@email.com',
            'password': '1234567890'
        })
        assert res.status_code == 302
        assert res.location == 'http://localhost/suppliers'
        assert any('Secure;' in c for c in res.headers.getlist('Set-Cookie'))

    def test_should_redirect_to_homepage_on_buyer_login(self):
        self.data_api_client.authenticate_user.return_value = self.user(123, "email@email.com", None, None, 'Name')
        res = self.client.post("/user/login", data={
            'email_address': 'valid@email.com',
            'password': '1234567890'
        })
        assert res.status_code == 302
        assert res.location == 'http://localhost/'
        assert any('Secure;' in c for c in res.headers.getlist('Set-Cookie'))

    def test_should_redirect_logged_in_supplier_to_supplier_dashboard(self):
        self.login_as_supplier()
        res = self.client.get("/user/login")
        assert res.status_code == 302
        assert res.location == 'http://localhost/suppliers'

    def test_should_redirect_logged_in_buyer_to_homepage(self):
        self.login_as_buyer()
        res = self.client.get("/user/login")
        assert res.status_code == 302
        assert res.location == 'http://localhost/'

    def test_should_redirect_logged_in_admin_to_admin_dashboard(self):
        self.login_as_admin()
        res = self.client.get("/user/login")
        assert res.status_code == 302
        assert res.location == 'http://localhost/admin'

    def test_should_redirect_to_dashboard_if_next_url_is_unsafe(self):
        self.login_as_supplier()
        res = self.client.get("/user/login?next=//example.com")
        assert res.status_code == 302
        assert res.location == 'http://localhost/suppliers'

    def test_should_redirect_to_dashboard_if_next_url_is_not_http(self):
        self.login_as_admin()
        res = self.client.get("/user/login?next=file:example.pdf")
        assert res.status_code == 302
        assert res.location == 'http://localhost/admin'

    def test_should_redirect_to_next_url_absolutized(self):
        self.login_as_supplier()
        res = self.client.get("/user/login?next=dolphinsbarn")
        assert res.status_code == 302
        assert res.location == 'http://localhost/user/dolphinsbarn'

    def test_should_redirect_to_next_url_for_simple_auth_uri(self):
        self.login_as_supplier()
        res = self.client.get("/user/login?next=@example.com")
        assert res.status_code == 302
        assert res.location == 'http://localhost/user/@example.com'

    def test_should_redirect_logged_in_admin_to_next_url_if_admin_app(self):
        self.login_as_admin()
        res = self.client.get("/user/login?next=/admin/foo-bar")
        assert res.status_code == 302
        assert res.location == 'http://localhost/admin/foo-bar'

    def test_should_redirect_logged_in_supplier_to_next_url_if_supplier_app(self):
        self.login_as_supplier()
        res = self.client.get("/user/login?next=/suppliers/foo-bar")
        assert res.status_code == 302
        assert res.location == 'http://localhost/suppliers/foo-bar'

    def test_should_strip_whitespace_surrounding_login_email_address_field(self):
        self.client.post("/user/login", data={
            'email_address': '  valid@email.com  ',
            'password': '1234567890'
        })
        self.data_api_client.authenticate_user.assert_called_with('valid@email.com', '1234567890')

    def test_should_not_strip_whitespace_surrounding_login_password_field(self):
        self.client.post("/user/login", data={
            'email_address': 'valid@email.com',
            'password': '  1234567890  '
        })
        self.data_api_client.authenticate_user.assert_called_with(
            'valid@email.com', '  1234567890  ')

    def test_ok_next_url_redirects_supplier_on_login(self):
        res = self.client.post("/user/login?next=/suppliers/bar-foo",
                               data={
                                   'email_address': 'valid@email.com',
                                   'password': '1234567890'
                               })
        assert res.status_code == 302
        assert res.location == 'http://localhost/suppliers/bar-foo'

    def test_ok_next_url_redirects_buyer_on_login(self):
        self.data_api_client.authenticate_user.return_value = self.user(123, "email@email.com", None, None, 'Name')
        res = self.client.post("/user/login?next=/bar-foo",
                               data={
                                   'email_address': 'valid@email.com',
                                   'password': '1234567890'
                               })
        assert res.status_code == 302
        assert res.location == 'http://localhost/bar-foo'

    def test_bad_next_url_takes_supplier_user_to_dashboard(self):
        res = self.client.post("/user/login?next=http://badness.com",
                               data={
                                   'email_address': 'valid@email.com',
                                   'password': '1234567890'
                               })
        assert res.status_code == 302
        assert res.location == 'http://localhost/suppliers'

    def test_bad_next_url_takes_buyer_user_to_homepage(self):
        self.data_api_client.authenticate_user.return_value = self.user(123, "email@email.com", None, None, 'Name')
        res = self.client.post("/user/login?next=http://badness.com",
                               data={
                                   'email_address': 'valid@email.com',
                                   'password': '1234567890'
                               })
        assert res.status_code == 302
        assert res.location == 'http://localhost/'

    def test_should_have_cookie_on_redirect(self):
        self.app.config['SESSION_COOKIE_DOMAIN'] = '127.0.0.1'
        self.app.config['SESSION_COOKIE_SECURE'] = True
        res = self.client.post("/login", data={
            'email_address': 'valid@email.com',
            'password': '1234567890'
        })

        properties = ['Secure', 'HttpOnly', 'Domain=127.0.0.1', 'Path=/']
        for prop in properties:
            assert any(prop in c for c in res.headers.getlist('Set-Cookie'))

        cookie_value = self.get_cookie_by_name(res, 'dm_session')
        assert cookie_value['dm_session'] is not None

    def test_should_redirect_to_login_on_logout(self):
        res = self.client.post('/user/logout')
        assert res.status_code == 302
        assert res.location == 'http://localhost/user/login'

    def test_should_expire_session_vars_on_logout(self):
        self.login_as_supplier()
        with self.client.session_transaction() as session:
            session['company_name'] = "Acme Corp"

        self.client.post('/user/logout')

        with self.client.session_transaction() as session:
            assert session.get('company_name') is None

    @mock.patch("app.main.views.auth.logout_user")
    def test_visiting_logout_should_logout(self, logout_user):
        self.login_as_supplier()
        res = self.client.get('/user/logout')
        assert logout_user.called
        assert res.status_code == 302
        assert res.location == 'http://localhost/user/login'

    def test_should_return_a_403_for_invalid_login(self):
        self.data_api_client.authenticate_user.return_value = None

        response = self.client.post("/user/login", data={
            'email_address': 'valid@email.com',
            'password': '1234567890'
        })
        assert self.strip_all_whitespace(str(NO_ACCOUNT_MESSAGE)) \
            in self.strip_all_whitespace(response.get_data(as_text=True))

        document = html.fromstring(response.get_data(as_text=True))
        error_summary_links = document.cssselect('div.govuk-error-summary a')

        assert len(error_summary_links) == 2
        assert error_summary_links[0].attrib['href'] == '#input-email_address'
        assert error_summary_links[1].attrib['href'] == '#input-password'

        assert response.status_code == 403

    @mock.patch('app.main.views.auth.are_new_frameworks_live')
    def test_should_show_banner_when_needed_when_403(self, are_new_frameworks_live):
        are_new_frameworks_live.return_value = True
        self.data_api_client.authenticate_user.return_value = None
        res = self.client.post("/user/login", data={
            'email_address': 'valid@email.com',
            'password': '1234567890'
        })
        assert res.status_code == 403
        assert "Important information" in res.get_data(as_text=True)

    def test_should_be_validation_error_if_no_email_or_password(self):
        res = self.client.post("/user/login", data={})
        content = self.strip_all_whitespace(res.get_data(as_text=True))
        assert res.status_code == 400
        assert self.strip_all_whitespace(EMAIL_EMPTY_ERROR_MESSAGE) in content
        assert self.strip_all_whitespace(LOGIN_PASSWORD_EMPTY_ERROR_MESSAGE) in content

    def test_should_be_validation_error_if_invalid_email(self):
        res = self.client.post("/user/login", data={
            'email_address': 'invalid',
            'password': '1234567890'
        })
        content = self.strip_all_whitespace(res.get_data(as_text=True))
        assert res.status_code == 400
        assert self.strip_all_whitespace(EMAIL_INVALID_ERROR_MESSAGE) in content

    @mock.patch('app.main.views.auth.are_new_frameworks_live')
    def test_should_show_banner_when_needed_when_400(self, are_new_frameworks_live):
        are_new_frameworks_live.return_value = True
        res = self.client.post("/user/login", data={})
        assert res.status_code == 400
        assert "Important information" in res.get_data(as_text=True)


class TestLoginFormIsAccessible(BaseApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.auth.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def _forms_and_inputs_specify_input_purpose(self, url, expected_title, expected_lede=None):
        response = self.client.get(url)
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))

        page_title = document.xpath('normalize-space(string(//main[@id="main-content"]//h1))')
        assert expected_title == page_title

        if expected_lede:
            page_lede = document.xpath('normalize-space(string(//main[@id="main-content"]//p[@class="govuk-body-l"]))')
            assert expected_lede == page_lede

        forms = document.xpath('//main[@id="content"]//form')

        for form in forms:
            assert form.get("autocomplete") != "off"
            non_hidden_inputs = form.xpath('//input[@type!="hidden"]')

            for input in non_hidden_inputs:
                if input.get("type") != "submit":
                    assert input.get("autocomplete") in VALID_INPUT_PURPOSES

    def test_login_form_and_inputs_specify_input_purpose(self):
        self._forms_and_inputs_specify_input_purpose(
            "/user/login",
            "Log in to the Digital Marketplace"
        )

    def test_request_password_reset_form_and_inputs_specify_input_purpose(self):
        self._forms_and_inputs_specify_input_purpose(
            "/user/reset-password",
            "Reset password"
        )

    @mock.patch('app.main.views.reset_password.data_api_client')
    def test_reset_password_form_and_inputs_specify_input_purpose(self, data_api_client):
        data_api_client.get_user.return_value = self.user(
            123, "email@email.com", 1234, 'email', 'name'
        )
        token = generate_token(
            {
                "user": 123,
                "email": 'email@email.com',
            },
            self.app.config['SHARED_EMAIL_KEY'],
            self.app.config['RESET_PASSWORD_TOKEN_NS'])

        url = '/user/reset-password/{}'.format(token)

        self._forms_and_inputs_specify_input_purpose(
            url,
            "Reset password",
            "Reset password for email@email.com"
        )
