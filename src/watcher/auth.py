import os
import time
from typing import Dict, Optional

import httpx

# Cloud provider imports (optional dependencies)
try:
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account
except ImportError:
    pass

try:
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest
except ImportError:
    pass

try:
    from azure.identity import DefaultAzureCredential
except ImportError:
    pass


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    pass


# Global state for token caching
_token_cache = {}


def _detect_cloud_environment() -> Optional[str]:
    """Detect the current cloud environment."""
    # Check for GCP
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.path.exists(
        "/var/run/secrets/kubernetes.io/serviceaccount/token"
    ):
        try:
            response = httpx.get(
                "http://metadata.google.internal/computeMetadata/v1/",
                headers={"Metadata-Flavor": "Google"},
                timeout=2.0,
            )
            if response.status_code == 200:
                return "gcp"
        except:
            pass

    # Check for Azure
    if os.getenv("AZURE_TENANT_ID") or os.getenv("AZURE_CLIENT_ID"):
        try:
            response = httpx.get(
                "http://169.254.169.254/metadata/instance",
                headers={"Metadata": "true"},
                timeout=2.0,
            )
            if response.status_code == 200:
                return "azure"
        except:
            pass

    # Check for AWS
    if os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("AWS_REGION"):
        try:
            response = httpx.get(
                "http://169.254.169.254/latest/meta-data/", timeout=2.0
            )
            if response.status_code == 200:
                return "aws"
        except:
            pass

    return None


def _get_gcp_token(service_account_path: Optional[str] = None) -> str:
    """Get GCP access token."""
    cache_key = f"gcp_{service_account_path or 'metadata'}"

    # Check cache
    if cache_key in _token_cache:
        token, expiry = _token_cache[cache_key]
        if time.time() < expiry:
            return token

    # Try metadata server first
    if not service_account_path:
        try:
            response = httpx.get(
                "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
                headers={"Metadata-Flavor": "Google"},
                timeout=10.0,
            )
            response.raise_for_status()
            token_data = response.json()
            token = token_data["access_token"]
            # Cache for 50 minutes
            _token_cache[cache_key] = (token, time.time() + 3000)
            return token
        except Exception as e:
            raise AuthenticationError(
                f"Failed to get GCP access token from metadata server: {e}"
            )

    # Use service account file
    try:
        credentials = service_account.Credentials.from_service_account_file(
            service_account_path
        )
        credentials.refresh(Request())
        token = credentials.token
        # Cache for 50 minutes
        _token_cache[cache_key] = (token, time.time() + 3000)
        return token
    except NameError:
        raise AuthenticationError(
            "google-auth library not installed. Install with: pip install etl-watcher-sdk[gcp]"
        )
    except Exception as e:
        raise AuthenticationError(
            f"Failed to get GCP access token from service account: {e}"
        )


def _get_azure_token() -> str:
    """Get Azure access token."""
    cache_key = "azure_managed_identity"

    # Check cache
    if cache_key in _token_cache:
        token, expiry = _token_cache[cache_key]
        if time.time() < expiry:
            return token

    try:
        # Use Azure SDK if available
        credential = DefaultAzureCredential()
        token = credential.get_token("https://management.azure.com/.default").token
        # Cache for 50 minutes
        _token_cache[cache_key] = (token, time.time() + 3000)
        return token
    except NameError:
        # Fallback to manual metadata server call
        try:
            response = httpx.get(
                "http://169.254.169.254/metadata/identity/oauth2/token",
                params={
                    "api-version": "2018-02-01",
                    "resource": "https://management.azure.com/",
                },
                headers={"Metadata": "true"},
                timeout=10.0,
            )
            response.raise_for_status()
            token_data = response.json()
            token = token_data["access_token"]
            # Cache for 50 minutes
            _token_cache[cache_key] = (token, time.time() + 3000)
            return token
        except Exception as e:
            raise AuthenticationError(f"Failed to get Azure access token: {e}")
    except Exception as e:
        raise AuthenticationError(f"Failed to get Azure access token: {e}")


def _get_aws_credentials() -> tuple[str, str, Optional[str]]:
    """Get AWS credentials."""
    cache_key = "aws_credentials"

    # Check cache
    if cache_key in _token_cache:
        creds, expiry = _token_cache[cache_key]
        if time.time() < expiry:
            return creds

    # Try metadata server first
    try:
        metadata_url = (
            "http://169.254.169.254/latest/meta-data/iam/security-credentials/"
        )
        response = httpx.get(metadata_url, timeout=10.0)
        response.raise_for_status()
        role_name = response.text.strip()

        creds_url = f"http://169.254.169.254/latest/meta-data/iam/security-credentials/{role_name}"
        response = httpx.get(creds_url, timeout=10.0)
        response.raise_for_status()
        creds_data = response.json()

        creds = (
            creds_data["AccessKeyId"],
            creds_data["SecretAccessKey"],
            creds_data.get("Token"),
        )
        # Cache for 50 minutes
        _token_cache[cache_key] = (creds, time.time() + 3000)
        return creds
    except Exception as e:
        # Fall back to environment variables
        access_key = os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        session_token = os.getenv("AWS_SESSION_TOKEN")

        if not access_key or not secret_key:
            raise AuthenticationError("AWS credentials not found")

        creds = (access_key, secret_key, session_token)
        # Cache for 50 minutes
        _token_cache[cache_key] = (creds, time.time() + 3000)
        return creds


def _sign_aws_request(
    method: str,
    url: str,
    headers: Dict[str, str],
    body: str = "",
    region: str = "us-east-1",
) -> Dict[str, str]:
    """Sign AWS request with credentials."""
    try:
        access_key, secret_key, session_token = _get_aws_credentials()

        request = AWSRequest(method=method, url=url, data=body, headers=headers)
        SigV4Auth(
            credentials={
                "access_key": access_key,
                "secret_key": secret_key,
                "token": session_token,
            },
            region_name=region,
            service="execute-api",
        ).add_auth(request)

        return dict(request.headers)
    except NameError:
        raise AuthenticationError(
            "boto3 library not installed. Install with: pip install etl-watcher-sdk[aws]"
        )
    except Exception as e:
        raise AuthenticationError(f"Failed to sign AWS request: {e}")


def _create_auth_provider(auth: Optional[str] = None):
    """Create authentication provider - returns a simple object with get_headers method."""

    class AuthProvider:
        def __init__(self, auth_type: str, auth_value: Optional[str] = None):
            self.auth_type = auth_type
            self.auth_value = auth_value
            self._aws_credentials = None

        def get_headers(self) -> Dict[str, str]:
            if self.auth_type == "none":
                return {}
            elif self.auth_type == "bearer":
                return {"Authorization": f"Bearer {self.auth_value}"}
            elif self.auth_type == "gcp":
                token = _get_gcp_token(self.auth_value)
                return {"Authorization": f"Bearer {token}"}
            elif self.auth_type == "azure":
                token = _get_azure_token()
                return {"Authorization": f"Bearer {token}"}
            elif self.auth_type == "aws":
                # AWS requires per-request signing, store credentials internally
                if self._aws_credentials is None:
                    try:
                        self._aws_credentials = _get_aws_credentials()
                    except Exception as e:
                        raise AuthenticationError(f"Failed to get AWS credentials: {e}")
                return {
                    "X-AWS-Auth": "true"
                }  # Signal to client that AWS signing is needed

        def get_aws_credentials(self) -> tuple[str, str, Optional[str]]:
            """Get AWS credentials for request signing."""
            if self._aws_credentials is None:
                self._aws_credentials = _get_aws_credentials()
            return self._aws_credentials

        def refresh_if_needed(self) -> None:
            # Tokens are cached and auto-refresh
            pass

    if auth is None:
        # Auto-detect
        cloud_env = _detect_cloud_environment()
        if cloud_env == "gcp":
            return AuthProvider("gcp")
        elif cloud_env == "azure":
            return AuthProvider("azure")
        elif cloud_env == "aws":
            return AuthProvider("aws")
        else:
            return AuthProvider("none")

    elif isinstance(auth, str):
        # Check if it's a file path (GCP service account)
        if auth.endswith(".json") and os.path.exists(auth):
            return AuthProvider("gcp", auth)
        else:
            # Assume it's a bearer token
            return AuthProvider("bearer", auth)
