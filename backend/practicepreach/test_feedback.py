"""POST /feedback must not lose a message just because the mail fails. The container's
local disk is wiped on every Cloud Run cold start, and Gmail broke silently for weeks
(revoked app password), so each feedback is stored in GCS first and mailed second; only
if *both* fail does the visitor get an error."""

import asyncio
import json
import logging
import re
import threading

import pytest
from fastapi.testclient import TestClient

from practicepreach import fast

SECRET_TEXT = "GEHEIMER-FEEDBACK-TEXT: Größe der Schrift"


class FakeBlob:
    def __init__(self, bucket, name):
        self.bucket, self.name = bucket, name

    def upload_from_string(self, data, content_type=None, timeout=None):
        if self.bucket.client.fail:
            raise RuntimeError("gcs down")
        self.bucket.client.uploads.append(
            {"bucket": self.bucket.name, "name": self.name, "data": data,
             "content_type": content_type, "timeout": timeout}
        )


class FakeBucket:
    def __init__(self, client, name):
        self.client, self.name = client, name

    def blob(self, name):
        return FakeBlob(self, name)


class FakeGcsClient:
    def __init__(self, fail=False):
        self.fail = fail
        self.uploads = []

    def bucket(self, name):
        return FakeBucket(self, name)


class FakeSMTP:
    sent = []
    fail = False
    created = []

    def __init__(self, host, port, timeout=None):
        try:
            asyncio.get_running_loop()
            in_event_loop = True
        except RuntimeError:
            in_event_loop = False
        FakeSMTP.created.append({"timeout": timeout, "in_event_loop": in_event_loop})

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        pass

    def login(self, user, password):
        if FakeSMTP.fail:
            raise ConnectionError("Connection unexpectedly closed")

    def send_message(self, msg):
        FakeSMTP.sent.append(msg)


@pytest.fixture(autouse=True)
def env(monkeypatch, tmp_path):
    FakeSMTP.sent, FakeSMTP.created, FakeSMTP.fail = [], [], False
    monkeypatch.setattr(fast.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(fast, "GMAIL_USER", "me@example.com")
    monkeypatch.setattr(fast, "GMAIL_APP_PASSWORD", "pw")
    monkeypatch.setattr(fast, "USE_GCS_CHROMA", True)
    monkeypatch.setattr(fast, "GCS_CHROMA_PATH", "gs://bkt/data/chroma_store_gemini")
    monkeypatch.setattr(fast, "FEEDBACK_FILE", tmp_path / "feedback.json")
    gcs = FakeGcsClient()
    monkeypatch.setattr(fast, "_gcs_client", lambda: gcs)
    return gcs


@pytest.fixture
def gcs(env):
    return env


def post(text=SECRET_TEXT, email="a@b.de", from_url="/zusammenfassungen/101_Zusatzpunkt%202"):
    client = TestClient(fast.app)  # no `with`: lifespan (and Rag()) is not started
    return client.post("/feedback", json={"text": text, "email": email, "from_url": from_url})


def test_empty_text_is_rejected(gcs):
    # characterisation: green on the old code too
    assert post(text="   ").status_code == 400
    assert gcs.uploads == [] and FakeSMTP.sent == []


def test_feedback_is_stored_in_gcs(gcs):
    assert post().status_code == 200
    assert len(gcs.uploads) == 1
    up = gcs.uploads[0]
    assert up["bucket"] == "bkt"
    assert re.fullmatch(r"feedback/\d{8}T\d{6}-[0-9a-f]{8}\.json", up["name"]), up["name"]
    assert up["content_type"] == "application/json"
    assert up["timeout"], "a hung GCS call must not hang the request"
    assert SECRET_TEXT in up["data"], "umlauts must be stored as-is, not \\u-escaped"
    entry = json.loads(up["data"])
    assert entry["text"] == SECRET_TEXT
    assert entry["email"] == "a@b.de"
    assert entry["from_url"] == "/zusammenfassungen/101_Zusatzpunkt%202"
    assert entry["timestamp"]
    assert up["name"] == f"feedback/{entry['id']}.json"


def test_each_feedback_gets_its_own_object(gcs):
    post(), post()
    names = {u["name"] for u in gcs.uploads}
    assert len(names) == 2


def test_failing_mail_does_not_lose_the_feedback(gcs):
    FakeSMTP.fail = True
    assert post().status_code == 200
    assert len(gcs.uploads) == 1


def test_failing_gcs_still_succeeds_when_the_mail_goes_out(gcs):
    # characterisation: green on the old code too (it only knew the mail)
    gcs.fail = True
    assert post().status_code == 200
    assert len(FakeSMTP.sent) == 1


def test_visitor_gets_an_error_when_nothing_could_be_saved(gcs):
    gcs.fail = True
    FakeSMTP.fail = True
    assert post().status_code == 503


def test_mail_contains_text_and_id(gcs):
    post()
    body = FakeSMTP.sent[0].get_payload(decode=True).decode()
    assert SECRET_TEXT in body
    assert json.loads(gcs.uploads[0]["data"])["id"] in body


def test_mail_is_sent_off_the_event_loop_with_a_timeout(gcs):
    post()
    assert FakeSMTP.created, "no mail was attempted"
    assert FakeSMTP.created[0]["in_event_loop"] is False, "blocking SMTP inside the event loop"
    assert FakeSMTP.created[0]["timeout"], "SMTP without timeout can hang the request forever"


def test_log_has_metadata_but_never_the_text(gcs, caplog):
    with caplog.at_level(logging.DEBUG, logger="practicepreach.fast"):
        post()
    lines = [r.getMessage() for r in caplog.records if "eedback" in r.getMessage()]
    assert any("stored=True" in l and "mailed=True" in l for l in lines), lines
    assert not any(SECRET_TEXT in r.getMessage() for r in caplog.records)
    assert not any("a@b.de" in r.getMessage() for r in caplog.records)


def test_without_gcs_it_falls_back_to_the_local_file(monkeypatch, gcs):
    # characterisation: green on the old code too (local development)
    monkeypatch.setattr(fast, "USE_GCS_CHROMA", False)
    monkeypatch.setattr(fast, "GMAIL_USER", None)
    assert post().status_code == 200
    stored = json.loads(fast.FEEDBACK_FILE.read_text())
    assert [e["text"] for e in stored] == [SECRET_TEXT]
    assert gcs.uploads == []
