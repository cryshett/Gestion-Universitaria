"""
core/security.py
================
Funciones criptográficas y gestión de seguridad del sistema (adaptadas de mb-system):

- Hash y verificación de contraseñas con Argon2 (passlib + argon2-cffi).
- Creación y decodificación de JWT (access_token y refresh_token) firmados con HS256.
"""

import os
import uuid
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext

# Configuración de Clave Secreta y Algoritmos
SECRET_KEY: str = os.environ.get("SECRET_KEY", "universidad_secret_key_2026_mb_system_secure")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 15))
REFRESH_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("REFRESH_TOKEN_EXPIRE_MINUTES", 1440)) # 1 día
MAX_LOGIN_ATTEMPTS: int = int(os.environ.get("MAX_LOGIN_ATTEMPTS", 3))
LOCKOUT_MINUTES: int = int(os.environ.get("LOCKOUT_MINUTES", 5))

# Contexto de Criptografía con Argon2
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    """Genera el hash Argon2 de una contraseña en texto plano."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Compara una contraseña en texto plano contra su hash Argon2 almacenado.
    Retorna True si coincide, False en caso contrario.
    """
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


def create_access_token(subject: str, role: str) -> str:
    """Crea un JWT de acceso de vida corta."""
    now = datetime.utcnow()
    payload = {
        "sub": subject,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(subject: str, jti: str, expires_at: datetime) -> str:
    """Crea un JWT de refresh; el jti debe coincidir con el registrado en BD."""
    payload = {
        "sub": subject,
        "type": "refresh",
        "iat": datetime.utcnow(),
        "exp": expires_at,
        "jti": jti,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decodifica y valida la firma/expiración de cualquier JWT del sistema."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
