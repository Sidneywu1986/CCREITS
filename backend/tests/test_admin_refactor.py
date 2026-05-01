"""
TDD for Wave 4: Admin backend refactor
Verify the new layered architecture components.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

def test_schemas_import():
    from admin.schemas import LoginRequest, LoginResponse
    req = LoginRequest(username="admin", password="secret")
    assert req.username == "admin"
    assert req.password == "secret"
    
    resp = LoginResponse(code=200, message="ok")
    assert resp.code == 200

def test_utils_import():
    from admin.utils import DB_URL, sign_cookie, verify_cookie
    assert "postgres://" in DB_URL
    
    signed = sign_cookie("admin")
    assert signed != "admin"
    assert verify_cookie(signed) == "admin"
    assert verify_cookie("tampered") is None

def test_routes_import():
    from admin.routes import auth, dashboard, funds
    assert auth.api_router is not None
    assert dashboard.api_router is not None
    assert funds.api_router is not None

def test_directory_structure():
    base = os.path.join(os.path.dirname(__file__), '..', 'backend', 'admin')
    assert os.path.exists(os.path.join(base, 'app.py'))
    assert os.path.exists(os.path.join(base, 'utils.py'))
    assert os.path.exists(os.path.join(base, 'schemas.py'))
    assert os.path.exists(os.path.join(base, 'routes', 'auth.py'))
    assert os.path.exists(os.path.join(base, 'routes', 'dashboard.py'))
    assert os.path.exists(os.path.join(base, 'routes', 'funds.py'))

if __name__ == '__main__':
    test_schemas_import()
    print("✓ test_schemas_import")
    test_utils_import()
    print("✓ test_utils_import")
    test_routes_import()
    print("✓ test_routes_import")
    test_directory_structure()
    print("✓ test_directory_structure")
    print("\nAll Wave 4 refactor tests passed!")
