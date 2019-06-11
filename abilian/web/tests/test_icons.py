""""""
from abilian.web.action import FAIcon, Glyphicon, StaticIcon


def test_glyphicons() -> None:
    icon = Glyphicon("ok")
    assert icon.__html__() == '<i class="glyphicon glyphicon-ok"></i>'


def test_faicons() -> None:
    icon = FAIcon("check")
    assert icon.__html__() == '<i class="fa fa-check"></i>'


def test_staticicon(app):
    with app.test_request_context():
        icon = StaticIcon("path/to/icon.png")
        assert (
            icon.__html__()
            == '<img src="/static/path/to/icon.png" width="12" height="12" />'
        )

        icon = StaticIcon("path/to/icon.png", width=14)
        assert (
            icon.__html__()
            == '<img src="/static/path/to/icon.png" width="14" height="12" />'
        )

        icon = StaticIcon("path/to/icon.png", height=14)
        assert (
            icon.__html__()
            == '<img src="/static/path/to/icon.png" width="12" height="14" />'
        )

        icon = StaticIcon("path/to/icon.png", size=14)
        assert (
            icon.__html__()
            == '<img src="/static/path/to/icon.png" width="14" height="14" />'
        )

        icon = StaticIcon("path/to/icon.png", size=14, css="avatar")
        assert (
            icon.__html__()
            == '<img class="avatar" src="/static/path/to/icon.png" width="14" '
            'height="14" />'
        )
