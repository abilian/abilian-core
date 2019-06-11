from flask import redirect, request, url_for
from flask_login import login_user

from abilian.core.models.subjects import User
from abilian.web.admin.panel import AdminPanel


class ImpersonatePanel(AdminPanel):
    id = "impersonate"
    label = "Impersonate"
    icon = "user"

    def get(self):
        user_email = request.args.get("email")
        if not user_email:
            return "UI not done yet. Add '?email=...' at the end of this URL for now."

        user = User.query.filter(User.email == user_email).one()
        login_user(user)
        return redirect(url_for("main.home"))
