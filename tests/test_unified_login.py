from app.api.routes import auth

class Request:
    client = type("Client", (), {"host": "127.0.0.1"})()

def test_unified_dispatches_patient(monkeypatch):
    monkeypatch.setattr(auth, "lookup", lambda cur,email: ("patient", "p"))
    monkeypatch.setattr(auth, "authenticate_user", lambda email,password: {"patient_id":"p","login_email":email})
    monkeypatch.setattr(auth, "issue_refresh_token", lambda **kwargs: "fake-refresh-token")
    response=auth.unified_login(auth.LoginRequest(email="p@example.com",password="x"), Request())
    assert response["user"]["patient_id"] == "p"
    assert response["refresh_token"] == "fake-refresh-token"

def test_unified_dispatches_doctor_to_mfa(monkeypatch):
    monkeypatch.setattr(auth, "lookup", lambda cur,email: ("doctor", "a"))
    monkeypatch.setattr(auth, "check_rate_limit", lambda *args: None)
    monkeypatch.setattr(auth, "authenticate_doctor_password", lambda *args: ("a","d","d@example.com"))
    response=auth.unified_login(auth.LoginRequest(email="d@example.com",password="x"), Request())
    assert response["status"] == "mfa_required"

def test_unified_dispatches_admin(monkeypatch):
    monkeypatch.setattr(auth, "lookup", lambda cur,email: ("admin", "a"))
    monkeypatch.setattr(auth, "check_rate_limit", lambda *args: None)
    monkeypatch.setattr(auth, "authenticate_admin_with_lockout", lambda *args: {"role":"admin","email":"a@example.com","access_token":"token","account_id":"a"})
    monkeypatch.setattr(auth, "issue_refresh_token", lambda **kwargs: "fake-refresh-token")
    response=auth.unified_login(auth.LoginRequest(email="a@example.com",password="x"), Request())
    assert response["role"] == "admin"
    assert response["refresh_token"] == "fake-refresh-token"
