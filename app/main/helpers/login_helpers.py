from urllib.parse import urlparse, urljoin

from flask_login import current_user
from flask import request, redirect, url_for


def is_safe_url(next_url):
    """
    Return `True` if the url is safe to use in a redirect (ie it doesn't point to
    an external host or change the scheme from http[s]).

    Returns `False` if url is empty.

    """
    if not next_url:
        return False

    app_host = urlparse(request.host_url).netloc
    next_url = urlparse(urljoin(request.host_url, next_url))

    return next_url.scheme in ['http', 'https'] and next_url.netloc == app_host


def redirect_logged_in_user(next_url=None, account_created=False):
    if is_safe_url(next_url):
        redirect_path = next_url
    elif current_user.role == 'supplier':
        redirect_path = '/suppliers'
    elif current_user.role.startswith('admin'):
        redirect_path = '/admin'
    else:
        redirect_path = url_for('external.index')

    # TODO: emit analytics event if account_created

    return redirect(redirect_path)


def get_user_dashboard_url(current_user_):
    if current_user_.role == 'supplier':
        return url_for('external.supplier_dashboard')
    elif current_user_.role == "buyer":
        return url_for('external.buyer_dashboard')
    elif current_user_.role.startswith('admin'):
        return url_for('external.admin_dashboard')

    return None


def is_there_a_live_g_cloud_framework(client):
    live_g_cloud_frameworks = list(
        filter(lambda f: f['family'] == 'g-cloud' and f['status'] == 'live', client.find_frameworks()['frameworks'])
    )

    return len(live_g_cloud_frameworks) > 0
