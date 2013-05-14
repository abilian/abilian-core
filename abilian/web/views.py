from flask import Blueprint


base = Blueprint('web', __name__,
                 template_folder='templates',
                 static_url_path='/static/base',
                 static_folder='static')