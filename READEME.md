<h4>Reverse Nginx for Superset</h4>
This repo is documented apache superset deployment with reverse Nginx and Gunicorn on the AWS, the pipeline built based on
- load data from mongodb 
- use python to do the data cleansing and aggregation
- transfer aggregated data to DWH, MySQL 
- connect DB with Apache Superset 

use airflow for the data pipeline orchestration, for we need not only `in-house` dashboard but the one that any user can view from public domain, like the Flask app, the easiest way is to use the revsere proxy nginx. 

####Init the venv 
```bash 
$pyenv activate superset 
```
####check the PYTHONPATH, can use `sys` module to check all the available path 
```bash
$ /home/ubuntu/.local/lib/python3.5/site-packages 
```
####Create a new config file

```bash 
$ vim /home/ubuntu/.local/lib/python3.5/site-packages/superset_config.py
```

####add the following line in that folder 
```bash 
from superset.security import SupersetSecurityManager
from flask import redirect, g, flash, request, session
from flask_appbuilder._compat import as_unicode
from flask_appbuilder.security.views import AuthDBView, AuthRemoteUserView
from flask_appbuilder.security.views import expose
from flask_appbuilder.security.manager import BaseSecurityManager
from flask_appbuilder import base
from flask_login import login_user, logout_user

# Uncomment to setup Public role name, no authentication needed
AUTH_ROLE_PUBLIC = 'Public'
# Will allow user self registration
#AUTH_USER_REGISTRATION = False
# The default user self registration role
#AUTH_USER_REGISTRATION_ROLE = "Gamma" 

from flask_appbuilder.security.manager import AUTH_DB, AUTH_LDAP, AUTH_REMOTE_USER
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
ROW_LIMIT = 5000
SUPERSET_WORKERS = 4
# You will be serving site on port 8000 from gunicorn which sits in front of flask, and then send to nginx
SUPERSET_WEBSERVER_PORT = 8088
#---------------------------------------------------------
# Flask App Builder configuration
#---------------------------------------------------------
# Your App secret key
#SECRET_KEY = "\2\1thisismyscretkey\1\2\e\y\y\h" 
# The SQLAlchemy connection string to your database backend 

# Flask-WTF flag for CSRF
CSRF_ENABLED = True
WTF_CSRF_ENABLED = False
ENABLE_PROXY_FIX =True
ENABLE_CORS= True

#your db connection 
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
```
####Install Redis 
######Upgrade apt-get 
```bash
$ sudo apt-get update
$ sudo apt-get upgrade
```
######Install the redis server
```bash
$ sudo apt-get install redis-server
```
####Change the redis config file
```bash
$ vim /etc/redis/redis.conf 
```
######Add the following lines to redis.conf
```bash
maxmemory 128mb
maxmemory-policy allkeys-lru
```
####Restart and enable redis on reboot
```bash
$ sudo systemctl restart redis-server.service
$ sudo systemctl enable redis-server.service 
```
######ensure redis shows up in htop
```bash 
$ htop
```

####Monitoring live
```bash 
$ redis-cli monitor
```
####Flush Cache
```bash 
$ redis-cli
flushall 
```

#### Set up Gunicorn 
```bash 
$ pip install gunicorn
$ gunicorn superset:app -b localhost:8000 &
```

#### Set up Nginx 
```bash
$ sudo apt-get install nginx
```

######here have two file_dirs need to config to get the nginx run 
```bash
$ sudo vim /etc/nginx/nginx.conf
```
######add the following lines 
```bash 
user www-data;
worker_processes auto;
pid /run/nginx.pid;
worker_rlimit_nofile 100480;

events {
        worker_connections 20000;
        # multi_accept on;
}
http {
        # Basic Settings

        sendfile on;
        tcp_nopush on;
        tcp_nodelay on;
        keepalive_timeout 65;
        types_hash_max_size 2048;
        # server_tokens off;

        # server_names_hash_bucket_size 64;
        # server_name_in_redirect off;

        include /etc/nginx/mime.types;
        default_type application/octet-stream;

        ssl_protocols TLSv1 TLSv1.1 TLSv1.2; # Dropping SSLv3, ref: POODLE
        ssl_prefer_server_ciphers on;

        # Logging Settings

        access_log /var/log/nginx/access.log;
        error_log /var/log/nginx/error.log;

        ##
        # Gzip Settings
        ##

        gzip on;
        gzip_disable "msie6";

        # gzip_vary on;
        # gzip_proxied any;
        # gzip_comp_level 6;
        # gzip_buffers 16 8k;
        # gzip_http_version 1.1;
        # gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

        ##
        # Virtual Host Configs
        ##
        #18.162.249.250
        server {
           server_name localhost;
           listen 8088;

        location / {
        proxy_pass http://127.0.0.1:8088;
        proxy_set_header HTTP_PROXY_REMOTE_USER $1;
        proxy_set_header Host $host:8088;
        proxy_set_header X-Real-IP $remote_addr;
       # proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          }
      }
        include /etc/nginx/conf.d/*.conf;
        include /etc/nginx/sites-enabled/*;
}
```
####config config files on the site-available folder 
```bash
$sudo vim /etc/nginx/sites-available/suprset.conf
```
```
server {
       listen   80; 
       server_name  18.162.249.250;
        large_client_header_buffers 4 16k;

      location / {
          proxy_buffers 16 4k;
          proxy_buffer_size 2k;
          proxy_pass http://127.0.0.1:8000;
         }

} 
```
#### hardlink this superset.conf into the sites-enabled folder
```bash 
$ sudo ln -s /etc/nginx/sites-available/superset.conf /etc/nginx/sites-enabled
```
#### Test for syntax
```bash 
$ sudo nginx -t
$ sudo nginx -s reload 
```

###### should see these below
```bash 
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

#### check nginx status 
```bash 
$ sudo systemctl status nginx
```
###### you will see the process similar to this below 
```bash 
 nginx.service - A high performance web server and a reverse proxy server
   Loaded: loaded (/lib/systemd/system/nginx.service; enabled; vendor preset: enabled)
   Active: active (running) since Wed 2019-11-06 02:48:06 UTC; 6h ago
  Process: 7566 ExecStop=/sbin/start-stop-daemon --quiet --stop --retry QUIT/5 --pidfile /run/nginx.pid (code=exited, status=0/SUCCESS)
  Process: 7053 ExecReload=/usr/sbin/nginx -g daemon on; master_process on; -s reload (code=exited, status=0/SUCCESS)
  Process: 7608 ExecStart=/usr/sbin/nginx -g daemon on; master_process on; (code=exited, status=0/SUCCESS)
  Process: 7604 ExecStartPre=/usr/sbin/nginx -t -q -g daemon on; master_process on; (code=exited, status=0/SUCCESS)
 Main PID: 7610 (nginx)
    Tasks: 17
   Memory: 170.2M
      CPU: 19.899s
   CGroup: /system.slice/nginx.service
           ├─7610 nginx: master process /usr/sbin/nginx -g daemon on; master_process on
           ├─7611 nginx: worker process                           
           ├─7612 nginx: worker process                           
           ├─7613 nginx: worker process                           
           ├─7614 nginx: worker process                           
           ├─7615 nginx: worker process                           
           ├─7616 nginx: worker process                           
           ├─7617 nginx: worker process                           
           ├─7618 nginx: worker process                           
           ├─7619 nginx: worker process                           
           ├─7622 nginx: worker process                           
           ├─7623 nginx: worker process                           
           ├─7624 nginx: worker process                           
           ├─7625 nginx: worker process                           
           ├─7626 nginx: worker process                           
           ├─7627 nginx: worker process                           
           └─7628 nginx: worker process                           

Nov 06 02:48:06 ip-172-31-9-152 systemd[1]: Starting A high performance web server and a reverse proxy server...
Nov 06 02:48:06 ip-172-31-9-152 systemd[1]: Started A high performance web server and a reverse proxy server.
```

the testing dashboard web page like this can be visit on the http://18.162.249.250/superset/dashboard/11/ 

Reference:
<ul>
<li><a href='https://flask-appbuilder.readthedocs.io/en/latest/security.html#role-based'>Flask role </a>
</li>
<li>
<a href='https://medium.com/ymedialabs-innovation/deploy-flask-app-with-nginx-using-gunicorn-and-supervisor-d7a93aa07c18'>Deploy flask app with nginx using gunicorn and supervisor</a>
</li>
</ul>