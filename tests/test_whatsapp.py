import base64
import hashlib
import hmac

from app.api.routes import whatsapp


def test_normalize_mobile_number_handles_twilio_sender():
    from app.services.users import normalize_mobile_number

    assert normalize_mobile_number("whatsapp:+91 98765-43210") == "+919876543210"
    assert normalize_mobile_number("0091 9876543210") == "+919876543210"


def test_twiml_escapes_message_text():
    response = whatsapp._twiml("<hello> & goodbye")
    assert response.media_type == "application/xml"
    assert "&lt;hello&gt; &amp; goodbye" in response.body.decode()


def test_twilio_signature_matches_sorted_form_parameters(monkeypatch):
    token = "test-token"
    url = "https://example.test/webhooks/whatsapp"
    params = {"Body": "hello", "From": "whatsapp:+919876543210"}
    payload = url + "".join(key + params[key] for key in sorted(params))
    signature = base64.b64encode(
        hmac.new(token.encode(), payload.encode(), hashlib.sha1).digest()
    ).decode()

    monkeypatch.setattr(whatsapp, "TWILIO_AUTH_TOKEN", token)
    assert whatsapp._valid_twilio_signature(url, params, signature)
    assert not whatsapp._valid_twilio_signature(url, params, "invalid")
