"""Regression coverage for FULL_SYSTEM_AUDIT.md P1 #13/#14: DoctorInviteRequest.email,
SignupRequest.email, and SignupRequest.profile_email were plain `str` with no format
validation, and mobile_number had no format/length check at all. Pure pydantic-model
tests — no DB, no route dispatch needed.
"""
import pytest
from pydantic import ValidationError

from app.api.routes.admin import DoctorInviteRequest
from app.api.routes.auth import SignupRequest


def _signup_kwargs(**overrides):
    base = dict(
        email="patient@example.com",
        password="Pass1234!",
        confirm_password="Pass1234!",
        name="Test Patient",
        age=30,
        mobile_number="9876543210",
        address="123 Test Street",
        profile_email="patient-contact@example.com",
        blood_group="O+",
    )
    base.update(overrides)
    return base


def test_doctor_invite_request_accepts_valid_email():
    assert DoctorInviteRequest(email="doctor@example.com").email == "doctor@example.com"


def test_doctor_invite_request_rejects_malformed_email():
    with pytest.raises(ValidationError):
        DoctorInviteRequest(email="not-an-email")


def test_signup_request_accepts_valid_input():
    request = SignupRequest(**_signup_kwargs())
    assert request.email == "patient@example.com"
    assert request.profile_email == "patient-contact@example.com"


@pytest.mark.parametrize("bad_email", ["not-an-email", "missing-domain@", "@missing-local.com", ""])
def test_signup_request_rejects_malformed_login_email(bad_email):
    with pytest.raises(ValidationError):
        SignupRequest(**_signup_kwargs(email=bad_email))


@pytest.mark.parametrize("bad_email", ["not-an-email", "missing-domain@"])
def test_signup_request_rejects_malformed_profile_email(bad_email):
    with pytest.raises(ValidationError):
        SignupRequest(**_signup_kwargs(profile_email=bad_email))


@pytest.mark.parametrize("bad_mobile", ["123", "abcdefghij", "1" * 20, ""])
def test_signup_request_rejects_implausible_mobile_number(bad_mobile):
    with pytest.raises(ValidationError):
        SignupRequest(**_signup_kwargs(mobile_number=bad_mobile))


@pytest.mark.parametrize("good_mobile", ["9876543210", "+91 98765 43210", "+1 (555) 123-4567"])
def test_signup_request_accepts_plausible_mobile_number_formats(good_mobile):
    request = SignupRequest(**_signup_kwargs(mobile_number=good_mobile))
    # The raw, user-typed format is preserved (not normalized) — only validated.
    assert request.mobile_number == good_mobile
