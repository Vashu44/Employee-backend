from fastapi import logger,Depends,HTTPException,status
from fastapi.security import OAuth2PasswordBearer,HTTPBearer
from datetime import datetime, timedelta
from jose import JWTError, jwt
import  redis
import os
from dotenv import load_dotenv
from model.usermodels import User
from passlib.context import CryptContext
load_dotenv()

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
# Initialize password context
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

security = HTTPBearer()  

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_REFRESH_SECRET_KEY = os.getenv("JWT_REFRESH_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

ACCESS_TOKEN_EXPIRY_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRY_MINUTES","15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS","7"))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRY_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def is_refresh_token_valid(user_id: int, refresh_token: str) -> bool:
    stored_token = get_refresh_token(user_id)
    return stored_token == refresh_token

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_REFRESH_SECRET_KEY, algorithm=JWT_ALGORITHM)

def verify_access_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None

def verify_refresh_token(token: str):
    try:
        payload = jwt.decode(token, JWT_REFRESH_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None

def store_refresh_token(user_id: int, refresh_token: str):
    """Store refresh token in Redis with expiry"""
    try:
        # Set token with expiry time
        expire_days = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
        redis_client.setex(
            name=f"refresh_token:{user_id}",
            time=timedelta(days=expire_days),
            value=refresh_token
        )
        return True
    except Exception as e:
        print(f"Redis error: {e}")
        return False

def get_refresh_token(user_id: int):
    """Get refresh token from Redis"""
    try:
        return redis_client.get(f"refresh_token:{user_id}")
    except Exception as e:
        print(f"Redis error: {e}")
        return None

def delete_refresh_token(user_id: int):
    """Delete refresh token from Redis"""
    try:
        redis_client.delete(f"refresh_token:{user_id}")
        return True
    except Exception as e:
        print(f"Redis error: {e}")
        return False
    
# JWT Helper Functions
def create_reset_token(email: str) -> str:
    """Create JWT token for password reset"""
    payload = {
        'email': email,
        'exp': datetime.utcnow() + timedelta(minutes= ACCESS_TOKEN_EXPIRY_MINUTES),
        'iat': datetime.utcnow(),
        'purpose': 'password_reset'
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token

def verify_reset_token(token: str) -> str:
    """Verify JWT token and return email"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        email = payload.get('email')
        purpose = payload.get('purpose')
        
        if not email or purpose != 'password_reset':
            logger.warning("Invalid JWT  token payload")
            return None
        return email
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {str(e)}")
        return None

def blacklist_access_token(token: str):
    redis_client.setex(f"blacklisted_token:{token}", timedelta(days=7), "true")
def is_token_blacklisted(token: str) -> bool:
    return redis_client.exists(f"blacklisted_token:{token}") == 1


def decode_access_token(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate token",
        )
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_role(allowed_roles: list[str]):
    def _require_role(payload: dict = Depends(decode_access_token)):
        user_role = payload.get("role")
        if user_role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Access denied")
        return payload
    return _require_role 


def validate_user_and_role(username: str, password: str, role: str, db):
    user = db.query(User).filter(User.username == username, User.role == role).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found or role mismatch")
    
    if not pwd_context.verify(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid password")

    return user
# Get user permissions (you can customize this based on your needs)
def get_user_permissions(role: str):
    permissions_map = {
        'hr': [
            'view_all_employees', 'edit_employee_details', 'delete_employee',
            'view_payroll', 'manage_attendance', 'view_reports', 'manage_leaves',
            'recruit_employees'
        ],
        'admin': [
            'view_team_members', 'edit_team_member_details', 'view_team_attendance',
            'approve_leaves', 'view_team_reports', 'assign_tasks', 'evaluate_performance'
        ],
        'employee': [
            'view_personal_details', 'edit_personal_profile', 'view_personal_attendance',
            'apply_leave', 'view_personal_payroll', 'view_assigned_tasks', 'submit_timesheets'
        ]
    }
    return permissions_map.get(role, [])