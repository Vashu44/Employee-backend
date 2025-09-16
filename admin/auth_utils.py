from fastapi import Request, Depends
from fastapi.responses import RedirectResponse
from typing import Optional

async def get_current_admin(request: Request):
    admin_username = request.session.get("admin_username")
    if not admin_username:
        return None
    return admin_username

def admin_required(request: Request, admin_username: Optional[str] = Depends(get_current_admin)):
    if not admin_username:
        # Not authenticated, redirect to login page
        return RedirectResponse(url="/admin", status_code=302)
    return admin_username
