from flask_appbuilder.security.manager import AUTH_DB, AUTH_LDAP, AUTH_REMOTE_USER
# ----------------------------------------------------
# AUTHENTICATION CONFIG
# ----------------------------------------------------
# Uncomment to setup Full admin role name
# AUTH_ROLE_ADMIN = 'Admin'

# Uncomment to setup Public role name, no authentication needed
AUTH_ROLE_PUBLIC = 'Public'

# Will allow user self registration
#AUTH_USER_REGISTRATION = False

# The default user self registration role
#AUTH_USER_REGISTRATION_ROLE = "Gamma" 

from superset.security import SupersetSecurityManager
from flask import redirect, g, flash, request, session
from flask_appbuilder._compat import as_unicode
from flask_appbuilder.security.views import AuthDBView, AuthRemoteUserView
from flask_appbuilder.security.views import expose
from flask_appbuilder.security.manager import BaseSecurityManager
from flask_appbuilder import base
from flask_login import login_user, logout_user


class RemoteUserMiddleware(object):
    def __init__(self, app):
        self.app = app
    def __call__(self, environ, start_response):
        user = environ.pop('HTTP_PROXY_REMOTE_USER', None)
        environ['REMOTE_USER'] = user
        return self.app(environ, start_response)

ADDITIONAL_MIDDLEWARE = [RemoteUserMiddleware, ]

class MiCustomRemoteUserView(AuthRemoteUserView):
    # Leave blank
    login_template = ''

    @expose('/login/')
    def login(self):
        # headers
        username = request.headers.get('HTTP_PROXY_REMOTE_USER')
        if g.user is not None and g.user.is_authenticated():
                return redirect(self.appbuilder.get_url_for_index)

        sm = self.appbuilder.sm
        session = sm.get_session
        user = session.query(sm.user_model).filter_by(username=username).first()
        if user is None and username:
            msg = ("User not allowed, {}".format(username))
            flash(as_unicode(msg), 'error')
            return redirect(self.appbuilder.get_url_for_login)

        if username:
            user = self.appbuilder.sm.auth_user_remote_user(username)
            if user is None:
                flash(as_unicode(self.invalid_login_message), 'warning')
            else:
                login_user(user)
        else:
            flash(as_unicode(self.invalid_login_message), 'warning')

        return redirect(self.appbuilder.get_url_for_index)

class MiCustomSecurityManager(SupersetSecurityManager):
    authremoteuserview = MiCustomRemoteUserView

PUBLIC_ROLE_LIKE_GAMMA = True
#---------------------------------------------------------
ROW_LIMIT = 5000
SUPERSET_WORKERS = 4
# You will be serving site on port 8000 from gunicorn which sits in front of flask, and then send to nginx
SUPERSET_WEBSERVER_PORT = 8088


# Flask-WTF flag for CSRF
CSRF_ENABLED = True
WTF_CSRF_ENABLED = False
ENABLE_PROXY_FIX =True
ENABLE_CORS= True

# Set this API key to enable Mapbox visualizations
MAPBOX_API_KEY = ''

#SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(DATA_DIR, "superset.db")
SQLALCHEMY_DATABASE_URI = "mysql+pymysql://root:password@127.0.0.1:3306/binance?charset=utf8"

ACHE_DEFAULT_TIMEOUT = 86400
CACHE_CONFIG = {
'CACHE_TYPE': 'redis',
'CACHE_DEFAULT_TIMEOUT': 86400,
'CACHE_KEY_PREFIX': 'superset_',
'CACHE_REDIS_HOST': 'localhost',
'CACHE_REDIS_PORT': 6379,
'CACHE_REDIS_DB': 1,
'CACHE_REDIS_URL': 'redis://localhost:6379/1'

}


