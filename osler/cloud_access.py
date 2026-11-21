"""Credencial adicional do app; o hash nunca é enviado ao navegador."""
import base64
import hashlib
import hmac
import secrets

ITERATIONS = 600_000


def password_hash(password):
    if len(password) < 14:
        raise ValueError('Use uma senha de pelo menos 14 caracteres.')
    salt = secrets.token_bytes(24)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, ITERATIONS)
    return f'pbkdf2_sha256${ITERATIONS}$'+base64.b64encode(salt).decode()+'$'+base64.b64encode(digest).decode()


def verify_password(password, stored):
    try:
        algorithm, rounds, salt, digest = stored.split('$')
        if algorithm != 'pbkdf2_sha256' or not ITERATIONS <= int(rounds) <= 2_000_000:
            return False
        result = hashlib.pbkdf2_hmac('sha256', password.encode(), base64.b64decode(salt,validate=True), int(rounds))
        return hmac.compare_digest(result, base64.b64decode(digest,validate=True))
    except (ValueError, TypeError, AttributeError):
        return False


def session_valid(session, stored, now):
    return (isinstance(session, (list,tuple)) and len(session)==2
            and session[0] == hashlib.sha256(stored.encode()).hexdigest()
            and isinstance(session[1], (float,int)) and 0 <= now-session[1] < 12*3600)
