"""Supabase authentication for Alpha Copilot backend."""

import httpx
import logging
from typing import Optional, Tuple

from agent.config import Config

logger = logging.getLogger(__name__)


class SupabaseAuth:
    """Authenticate with Supabase to get JWT for backend API calls.

    Mimics the frontend auth flow:
    1. Login with email/password to get access token
    2. Use access token as Bearer token for API calls
    3. Refresh token when needed
    """

    def __init__(self):
        self.supabase_url = Config.SUPABASE_URL
        self.supabase_anon_key = Config.SUPABASE_ANON_KEY
        self.email = Config.SUPABASE_EMAIL
        self.password = Config.SUPABASE_PASSWORD
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None

    def login(self) -> Tuple[bool, str]:
        """Login to Supabase with email/password to get access token."""
        if not all([self.supabase_url, self.supabase_anon_key, self.email, self.password]):
            missing = []
            if not self.supabase_url:
                missing.append("SUPABASE_URL")
            if not self.supabase_anon_key:
                missing.append("SUPABASE_ANON_KEY")
            if not self.email:
                missing.append("SUPABASE_EMAIL")
            if not self.password:
                missing.append("SUPABASE_PASSWORD")
            return False, f"Missing credentials: {', '.join(missing)}"

        try:
            response = httpx.post(
                f"{self.supabase_url}/auth/v1/token?grant_type=password",
                headers={
                    "apikey": self.supabase_anon_key,
                    "Content-Type": "application/json",
                },
                json={
                    "email": self.email,
                    "password": self.password,
                },
                timeout=15.0
            )

            if response.status_code == 200:
                data = response.json()
                self._access_token = data["access_token"]
                self._refresh_token = data.get("refresh_token")
                logger.info("Supabase login successful")
                return True, "Login successful"
            elif response.status_code == 400:
                error_msg = response.json().get("error_description", "Invalid credentials")
                logger.error(f"Supabase login failed: {error_msg}")
                return False, f"Invalid credentials: {error_msg}"
            elif response.status_code == 422:
                return False, "Invalid email format"
            else:
                logger.error(f"Supabase login failed: HTTP {response.status_code}")
                return False, f"Login failed: HTTP {response.status_code}"

        except httpx.ConnectError:
            logger.error(f"Cannot connect to Supabase: {self.supabase_url}")
            return False, f"Cannot connect to Supabase: {self.supabase_url}"
        except httpx.TimeoutException:
            logger.error("Supabase login timeout")
            return False, "Login timeout"
        except Exception as e:
            logger.exception("Supabase login error")
            return False, f"Login error: {str(e)}"

    def get_access_token(self) -> Optional[str]:
        """Get current access token, login if needed."""
        if not self._access_token:
            success, msg = self.login()
            if not success:
                logger.error(f"Failed to get access token: {msg}")
                return None
        return self._access_token

    def refresh(self) -> Tuple[bool, str]:
        """Refresh the access token using refresh token."""
        if not self._refresh_token:
            return self.login()

        try:
            response = httpx.post(
                f"{self.supabase_url}/auth/v1/token?grant_type=refresh_token",
                headers={
                    "apikey": self.supabase_anon_key,
                    "Content-Type": "application/json",
                },
                json={"refresh_token": self._refresh_token},
                timeout=15.0
            )

            if response.status_code == 200:
                data = response.json()
                self._access_token = data["access_token"]
                self._refresh_token = data.get("refresh_token", self._refresh_token)
                logger.info("Supabase token refreshed")
                return True, "Token refreshed"
            else:
                # Refresh failed, try full login
                logger.warning("Token refresh failed, attempting full login")
                return self.login()

        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return False, f"Refresh error: {str(e)}"

    def clear_tokens(self) -> None:
        """Clear cached tokens (for logout or forced re-auth)."""
        self._access_token = None
        self._refresh_token = None
