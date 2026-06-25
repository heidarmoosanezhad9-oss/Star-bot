from app.services.vip_trust_service import clamp_trust
from app.bot.handlers.orders import _parse_channel_input
from app.services.custom_button_service import parse_buttons_json


def test_clamp_trust_upper_bound():
    assert clamp_trust(150) == 100


def test_clamp_trust_lower_bound():
    assert clamp_trust(-20) == 0


def test_clamp_trust_normal():
    assert clamp_trust(55) == 55


def test_parse_channel_input_username_without_at():
    assert _parse_channel_input("mychannel") == "@mychannel"


def test_parse_channel_input_username_with_at():
    assert _parse_channel_input("@mychannel") == "@mychannel"


def test_parse_channel_input_numeric_id():
    assert _parse_channel_input("-1001234567890") == -1001234567890


def test_parse_channel_input_tme_link():
    assert _parse_channel_input("https://t.me/mychannel") == "@mychannel"


def test_parse_buttons_json_empty():
    assert parse_buttons_json(None) == []


def test_parse_buttons_json_valid():
    assert parse_buttons_json('[{"label": "a", "url": "https://x.com"}]') == [{"label": "a", "url": "https://x.com"}]


def test_parse_buttons_json_invalid():
    assert parse_buttons_json("not json") == []
