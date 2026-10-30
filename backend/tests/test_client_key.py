from starlette.requests import Request

from app.api.turns import _client_key


def _request(forwarded: str | None, peer: str = "10.0.0.9") -> Request:
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded else []
    return Request({"type": "http", "headers": headers, "client": (peer, 1234)})


def test_a_client_supplied_forwarded_value_cannot_pick_its_own_bucket() -> None:
    # nginx appends the real peer to whatever the client sent, so the real address is the last entry.
    assert _client_key(_request("6.6.6.6, 203.0.113.7")) == "203.0.113.7"
    assert _client_key(_request("1.1.1.1, 2.2.2.2, 203.0.113.7")) == "203.0.113.7"


def test_a_single_entry_and_a_missing_header_fall_back_sensibly() -> None:
    assert _client_key(_request("203.0.113.7")) == "203.0.113.7"
    assert _client_key(_request(None, peer="198.51.100.4")) == "198.51.100.4"
