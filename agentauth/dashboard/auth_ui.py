from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..core.database import SessionLocal
from ..core.models import AdminUser
from ..core.security import create_access_token, verify_password

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>AgentAuth - Login</title>
    <style>
        body {
            background-color: #0f172a;
            color: #f8fafc;
            font-family: 'Inter', sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .login-box {
            background: rgba(30, 41, 59, 0.7);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 40px;
            border-radius: 16px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
            width: 320px;
        }
        h2 { margin-top: 0; color: #38bdf8; text-align: center; }
        input {
            width: 100%;
            padding: 10px;
            margin: 10px 0;
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            color: white;
            box-sizing: border-box;
        }
        button {
            width: 100%;
            padding: 12px;
            background: #38bdf8;
            color: #0f172a;
            border: none;
            border-radius: 8px;
            font-weight: bold;
            cursor: pointer;
            margin-top: 20px;
        }
        button:hover { background: #0ea5e9; }
        .error { color: #ef4444; font-size: 0.9em; text-align: center; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>AgentAuth</h2>
        <form method="POST" action="/login">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
            {error_html}
        </form>
    </div>
</body>
</html>
"""


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    error = request.query_params.get("error")
    error_html = f"<div class='error'>{error}</div>" if error else ""
    return HTML_TEMPLATE.replace("{error_html}", error_html)


@router.post("/login")
def login_post(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    admin = db.query(AdminUser).filter(AdminUser.username == username).first()
    if not admin or not verify_password(password, str(admin.hashed_password)):
        return RedirectResponse(url="/login?error=Invalid+credentials", status_code=303)

    access_token = create_access_token(data={"sub": admin.username})

    response = RedirectResponse(url="/dashboard/", status_code=303)
    # Set HttpOnly cookie
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=1440 * 60,  # 1 day
        expires=1440 * 60,
        samesite="lax",
    )
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("access_token")
    return response
