import logging
from functools import lru_cache

import jwt
from jwt import PyJWKClient

from app.core.config import settings
from app.core.exceptions import UnauthorizedException

logger = logging.getLogger("crimelens.auth")

_ASYMMETRIC_ALGS = frozenset({"RS256", "ES256", "EdDSA"})


@lru_cache(maxsize=1)
def _jwks_url() -> str | None:
    if settings.SUPABASE_JWKS_URL:
        return settings.SUPABASE_JWKS_URL
    if settings.SUPABASE_URL:
        return f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
    return None


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient | None:
    url = _jwks_url()
    if not url:
        return None
    try:
        return PyJWKClient(url)
    except Exception as exc:
        logger.warning("Could not initialize JWKS client: %s", exc)
        return None


class AuthService:
    """
    Handles verifying Supabase JWT access tokens securely and extracting user identity.
    Does not generate tokens, as Supabase manages full authentication.
    """

    @staticmethod
    def _decode_with_audience(token: str, key, algorithms: list[str]) -> dict:
        try:
            return jwt.decode(
                token,
                key,
                algorithms=algorithms,
                audience="authenticated",
            )
        except jwt.InvalidAudienceError:
            return jwt.decode(
                token,
                key,
                algorithms=algorithms,
                options={"verify_aud": False},
            )

    @staticmethod
    def verify_token(token: str) -> dict:
        try:
            try:
                alg = jwt.get_unverified_header(token).get("alg", settings.JWT_ALGORITHM)
            except Exception:
                alg = settings.JWT_ALGORITHM

            use_jwks = (
                settings.JWT_VERIFICATION_METHOD == "jwks"
                or alg in _ASYMMETRIC_ALGS
            )
            client = _jwks_client() if use_jwks else None

            if use_jwks and client is not None:
                signing_key = client.get_signing_key_from_jwt(token)
                return AuthService._decode_with_audience(
                    token, signing_key.key, [alg]
                )

            # HS256 / legacy Supabase shared secret
            return AuthService._decode_with_audience(
                token, settings.JWT_SECRET, ["HS256"]
            )

        except jwt.ExpiredSignatureError:
            logger.warning("Supabase JWT verification failed: Token has expired")
            raise UnauthorizedException(detail="Token has expired")
        except jwt.InvalidAudienceError:
            logger.warning("Supabase JWT verification failed: Invalid token audience")
            raise UnauthorizedException(detail="Invalid token audience")
        except jwt.PyJWTError as e:
            logger.warning(f"Supabase JWT verification failed ({type(e).__name__}): {e}")
            raise UnauthorizedException(detail="Could not validate credentials")

