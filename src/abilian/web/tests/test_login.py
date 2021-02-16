from flask import Flask, jsonify, session
from flask_login import current_user


def test_test(app: Flask, client, login_user):
    @app.route("/dump-session")
    def dump_session():
        user = current_user
        return jsonify(
            session=dict(session), first_name=user.first_name, last_name=user.last_name
        )

    response = client.get("/dump-session")
    assert response.status_code == 200

    json = response.json
    assert json["first_name"] == login_user.first_name
    assert json["last_name"] == login_user.last_name
