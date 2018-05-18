from __future__ import absolute_import, print_function, unicode_literals

import json
import os
import subprocess
from tempfile import NamedTemporaryFile

import requests
from flask import Response, current_app, request

SKIPPED_URLS = [
    # FIXME: later
    "http://localhost/admin/settings"
]


class ValidationError(AssertionError):
    pass


def assert_valid(response):
    # type: (Response) -> None
    if response.direct_passthrough:
        return

    data = response.data
    assert isinstance(data, bytes)
    # assert response.status_code in [200, 302, 401]

    if response.status_code == 302:
        return

    if request.url in SKIPPED_URLS:
        return

    if response.mimetype == "text/html":
        validate_html(response)

    elif response.mimetype == "application/json":
        validate_json(response)

    else:
        raise AssertionError("Unknown mime type: " + response.mimetype)

    return


def validate_html(response):
    validate_html_using_htmlhint(response)
    validate_html_using_external_service(response)


def validate_html_using_htmlhint(response):
    with NamedTemporaryFile() as tmpfile:
        tmpfile.write(response.data)
        tmpfile.flush()
        try:
            subprocess.check_output(["htmlhint", tmpfile.name])
        except subprocess.CalledProcessError as e:
            print("htmllhint output:")
            print(e.output)
            msg = "HTML was not valid for URL: {}".format(request.url)
            raise ValidationError(msg)


def validate_html_using_external_service(response):
    validator_url = current_app.config.get("VALIDATOR_URL") or os.environ.get(
        "VALIDATOR_URL"
    )

    if not validator_url:
        return

    validator_response = requests.post(
        validator_url + "?out=json",
        response.data,
        headers={"Content-Type": response.mimetype},
    )

    body = validator_response.json()

    for message in body["messages"]:
        if message["type"] == "error":
            detail = "on line {} [{}]\n{}".format(
                message["lastLine"], message["extract"], message["message"]
            )
            msg = "Got a validation error for {}:\n{}".format(request.url, detail)
            raise ValidationError(msg)


def validate_json(response):
    try:
        json.loads(response.data)
    except BaseException:
        msg = "JSON was not valid for URL: {}".format(request.url)
        raise ValidationError(msg)
