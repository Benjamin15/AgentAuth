from agentauth.core.models import AdminUser
from agentauth.core.security import get_password_hash


def test_dashboard_middleware_unauthenticated(client):
    response = client.get("/dashboard/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_dashboard_middleware_authenticated(client, db_session):
    admin = AdminUser(username="testadmin2", hashed_password=get_password_hash("testpass"))
    db_session.add(admin)
    db_session.commit()

    # Log in to set the cookie
    client.post("/login", data={"username": "testadmin2", "password": "testpass"})

    response = client.get("/dashboard/", follow_redirects=False)
    assert response.status_code != 303


def test_dashboard_middleware_invalid_token(client):
    client.cookies.set("access_token", "Bearer invalid-jwt")
    response = client.get("/dashboard/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_auth_ui_login_logout(client, db_session):
    # Login page rendering
    res_login = client.get("/login")
    assert res_login.status_code == 200

    # Logout redirect
    res_logout = client.get("/logout", follow_redirects=False)
    assert res_logout.status_code == 303
    assert res_logout.headers["location"] == "/login"
