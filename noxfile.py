import nox

PYTHON_VERSIONS = ["3.6", "3.7", "3.8"]
PACKAGE = "abilian"


@nox.session(python="python3.6")
def lint(session):
    # session.env["LC_ALL"] = "en_US.UTF-8"
    session.install("poetry", "psycopg2-binary")
    session.run("poetry", "install", "-q")
    session.run("yarn", external=True)
    session.run("make", "lint-ci")


@nox.session(python=PYTHON_VERSIONS)
def pytest(session):
    # session.env["LC_ALL"] = "en_US.UTF-8"
    session.install("psycopg2-binary")

    cmd = "echo ; echo SQLALCHEMY_DATABASE_URI = $SQLALCHEMY_DATABASE_URI ; echo"
    session.run("sh", "-c", cmd, external=True)

    session.run("poetry", "install", "-q", external=True)
    session.run("yarn", external=True)

    session.run("pip", "check")
    session.run("pytest", "-q")


# TODO later
# @nox.session(python="3.8")
# def typeguard(session):
#     # session.env["LC_ALL"] = "en_US.UTF-8"
#     session.install("psycopg2-binary")
#     session.run("poetry", "install", "-q", external=True)
#     session.run("yarn", external=True)
#     session.run("pytest", f"--typeguard-packages={PACKAGE}")
