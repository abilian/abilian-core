#from flaskext.cache import Cache
#from flaskext.openid import OpenID
from flask.ext.mail import Mail
from flask_sqlalchemy import SQLAlchemy
from flask.ext.babel import Babel

# Create helpers
db = SQLAlchemy()
babel = Babel()
mail = Mail()

# Not needed yet
#oid = OpenID()
#cache = Cache()
