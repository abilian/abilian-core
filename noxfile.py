import time
from random import randint

import nox
from nox.sessions import Session

PYTHON_VERSIONS = ["3.6", "3.7", "3.8"]
PACKAGE = "abilian"
DB_DRIVERS = ["postgres", "postgres+pg8000"]

nox.options.reuse_existing_virtualenvs = True
nox.options.sessions = ("pytest", "lint")


@nox.session(python="python3.6")
def lint(session):
    session.install("psycopg2-binary")
    session.run("poetry", "install", "-q")
    session.run("yarn", external=True)
    session.run("make", "lint-ci")


@nox.session(python=PYTHON_VERSIONS)
def pytest(session):
    print("SQLALCHEMY_DATABASE_URI=", session.env.get("SQLALCHEMY_DATABASE_URI"))

    session.install("psycopg2-binary")

    session.run("poetry", "install", "-q", external=True)
    session.run("yarn", external=True)

    session.run("pip", "check")
    session.run("pytest", "-q")


@nox.session(python=PYTHON_VERSIONS)
@nox.parametrize("db_driver", DB_DRIVERS)
def dbtests(session: Session, db_driver):
    session.install("psycopg2-binary", "pg8000")

    db_name = f"bench{randint(0, 10000000)}"
    uri = f"{db_driver}:///{db_name}"
    print("SQLALCHEMY_DATABASE_URI=", uri)
    session.env["SQLALCHEMY_DATABASE_URI"] = uri

    session.run("createdb", db_name, external=True)

    session.run("poetry", "install", "-q", external=True)
    session.run("yarn", external=True)

    session.run("pip", "check")

    t0 = time.time()
    session.run("pytest", "-q")
    t1 = time.time()

    with open("benchmark-result.txt", "a") as fd:
        fd.write(f"{session.python} {db_driver} -> Elapsed time: {t1 - t0}\n")

    session.run("dropdb", db_name, external=True)


# TODO later
# @nox.session(python="3.8")
# def typeguard(session):
#     # session.env["LC_ALL"] = "en_US.UTF-8"
#     session.install("psycopg2-binary")
#     session.run("poetry", "install", "-q", external=True)
#     session.run("yarn", external=True)
#     session.run("pytest", f"--typeguard-packages={PACKAGE}")
