""""""
from typing import Any

import pytest
from pytest import raises

from .models import Setting, empty_value


def test_type_set() -> None:
    s = Setting()
    # registered base type: no failure
    s.type = "int"
    s.type = "bool"
    s.type = "json"
    s.type = "string"

    with raises(ValueError):
        s.type = "dummy type name"


OBJ = [1, 2, "été", {"1": "1", "2": "2"}]


@pytest.mark.parametrize(
    "type_,value",
    [
        ("int", 42),
        ("bool", True),
        ("bool", False),
        ("string", "test"),
        ("string", "bel été"),
        ("json", None),
        ("json", OBJ),
    ],
)
def test_set_get(type_: str, value: Any) -> None:
    s = Setting(key="key", type=type_)
    s.value = value
    assert s.value == value


def test_empty_value() -> None:
    s = Setting(key="key", type="json")
    assert s.value == empty_value


def test_service_facade(app, session):
    svc = app.services.get("settings")
    svc.set("key_1", 42, "int")
    session.flush()
    assert svc.get("key_1") == 42

    # new key with no type: raise error:
    with raises(ValueError):
        svc.set("key_err", 42)

    # key already with type_, this should not raise an error
    svc.set("key_1", 24)
    session.flush()
    assert svc.get("key_1") == 24

    svc.delete("key_1")
    session.flush()
    with raises(KeyError):
        svc.get("key_1")

    # delete: silent by default
    svc.delete("non_existent")

    # delete: non-silent
    with raises(KeyError):
        svc.delete("non_existent", silent=False)

    # tricky use case: ask key delete, set it later, then flush
    svc.set("key_1", 42, "int")
    session.flush()
    svc.delete("key_1")
    svc.set("key_1", 1)
    session.flush()
    assert svc.get("key_1") == 1

    # list keys
    svc.set("key_2", 2, "int")
    svc.set("other", "azerty", "string")
    session.flush()
    assert sorted(svc.keys()) == ["key_1", "key_2", "other"]
    assert sorted(svc.keys(prefix="key_")) == ["key_1", "key_2"]

    # as dict
    assert svc.as_dict() == {"other": "azerty", "key_1": 1, "key_2": 2}
    assert svc.as_dict(prefix="key_") == {"key_1": 1, "key_2": 2}


def test_namespace(app, session):
    svc = app.services.get("settings")
    ns = svc.namespace("test")
    ns.set("1", 42, "int")
    session.flush()
    assert ns.get("1") == 42
    assert svc.get("test:1") == 42

    ns.set("sub:2", 2, "int")
    svc.set("other", "not in NS", "string")
    session.flush()
    assert sorted(ns.keys()) == ["1", "sub:2"]
    assert sorted(svc.keys()) == ["other", "test:1", "test:sub:2"]

    # sub namespace test:sub:
    sub = ns.namespace("sub")
    assert sub.keys() == ["2"]
    assert sub.get("2") == 2

    sub.set("1", 1, "int")
    session.flush()
    assert sub.get("1") == 1
    assert ns.get("1") == 42
    assert sorted(svc.keys()) == ["other", "test:1", "test:sub:1", "test:sub:2"]

    # as dict
    assert sub.as_dict() == {"1": 1, "2": 2}
    assert ns.as_dict(prefix="sub:") == {"sub:1": 1, "sub:2": 2}
    assert ns.as_dict() == {"1": 42, "sub:1": 1, "sub:2": 2}
    assert svc.as_dict() == {
        "other": "not in NS",
        "test:1": 42,
        "test:sub:1": 1,
        "test:sub:2": 2,
    }

    # deletion
    sub.delete("1")
    sub.delete("2")
    session.flush()
    assert sub.keys() == []
    assert ns.keys() == ["1"]
    assert sorted(svc.keys()) == ["other", "test:1"]
