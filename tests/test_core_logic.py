from app.services.vip_trust_service import clamp_trust
from app.bot.handlers.orders import _parse_channel_input


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
