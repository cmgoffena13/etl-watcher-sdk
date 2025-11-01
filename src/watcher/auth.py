import os
import time
from typing import Dict, Optional

from watcher.http_client import ProductionHTTPClient

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


def _detect_cloud_environment(http_client: ProductionHTTPClient) -> Optional[str]:
    """Detect the current cloud environment."""
    # Check for GCP
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.path.exists(
        "/var/run/secrets/kubernetes.io/serviceaccount/token"
    ):
        try:
            response = http_client.get(
                "http://metadata.google.internal/computeMetadata/v1/",
                headers={"Metadata-Flavor": "Google"},
            )
            if response.status_code == 200:
                return "gcp"
        except:
            pass

    # Check for Azure
    if os.getenv("AZURE_TENANT_ID") or os.getenv("AZURE_CLIENT_ID"):
        try:
            response = http_client.get(
                "http://169.254.169.254/metadata/instance",
                headers={"Metadata": "true"},
            )
            if response.status_code == 200:
                return "azure"
        except:
            pass

    # Check for AWS
    if os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("AWS_REGION"):
        try:
            response = http_client.get("http://169.254.169.254/latest/meta-data/")
            if response.status_code == 200:
                return "aws"
        except:
            pass

    return None


def _get_gcp_token(
    cache: Dict,
    http_client: ProductionHTTPClient,
    service_account_path: Optional[str] = None,
) -> str:
    """Get GCP access token."""
    cache_key = f"gcp_{service_account_path or 'metadata'}"

    # Check cache
    if cache_key in cache:
        token, expiry = cache[cache_key]
        if time.time() < expiry:
            return token

    # Try metadata server first
    if not service_account_path:
        try:
            response = http_client.get(
                "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
                headers={"Metadata-Flavor": "Google"},
            )
            response.raise_for_status()
            token_data = response.json()
            token = token_data["access_token"]
            # Cache for 50 minutes
            cache[cache_key] = (token, time.time() + 3000)
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
        cache[cache_key] = (token, time.time() + 3000)
        return token
    except NameError:
        raise AuthenticationError(
            "google-auth library not installed. Install with: pip install etl-watcher-sdk[gcp]"
        )
    except Exception as e:
        raise AuthenticationError(
            f"Failed to get GCP access token from service account: {e}"
        )


def _get_azure_token(
    cache: Dict,
    http_client: ProductionHTTPClient,
) -> str:
    """Get Azure access token."""
    cache_key = "azure_managed_identity"

    # Check cache
    if cache_key in cache:
        token, expiry = cache[cache_key]
        if time.time() < expiry:
            return token

    try:
        # Use Azure SDK if available
        credential = DefaultAzureCredential()
        token = credential.get_token("https://management.azure.com/.default").token
        # Cache for 50 minutes
        cache[cache_key] = (token, time.time() + 3000)
        return token
    except NameError:
        # Fallback to manual metadata server call
        try:
            response = http_client.get(
                "http://169.254.169.254/metadata/identity/oauth2/token",
                params={
                    "api-version": "2018-02-01",
                    "resource": "https://management.azure.com/",
                },
                headers={"Metadata": "true"},
            )
            response.raise_for_status()
            token_data = response.json()
            token = token_data["access_token"]
            # Cache for 50 minutes
            cache[cache_key] = (token, time.time() + 3000)
            return token
        except Exception as e:
            raise AuthenticationError(f"Failed to get Azure access token: {e}")
    except Exception as e:
        raise AuthenticationError(f"Failed to get Azure access token: {e}")


def _get_aws_credentials(
    cache: Dict,
    http_client: ProductionHTTPClient,
) -> tuple[str, str, Optional[str]]:
    """Get AWS credentials."""
    cache_key = "aws_credentials"

    # Check cache
    if cache_key in cache:
        creds, expiry = cache[cache_key]
        if time.time() < expiry:
            return creds

    # Try metadata server first
    try:
        metadata_url = (
            "http://169.254.169.254/latest/meta-data/iam/security-credentials/"
        )
        response = http_client.get(metadata_url)
        response.raise_for_status()
        role_name = response.text.strip()

        creds_url = f"http://169.254.169.254/latest/meta-data/iam/security-credentials/{role_name}"
        response = http_client.get(creds_url)
        response.raise_for_status()
        creds_data = response.json()

        creds = (
            creds_data["AccessKeyId"],
            creds_data["SecretAccessKey"],
            creds_data.get("Token"),
        )
        # Cache for 50 minutes
        cache[cache_key] = (creds, time.time() + 3000)
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
        cache[cache_key] = (creds, time.time() + 3000)
        return creds


def _sign_aws_request(
    method: str,
    url: str,
    headers: Dict[str, str],
    cache: Dict,
    http_client: ProductionHTTPClient,
    body: str = "",
    region: str = "us-east-1",
) -> Dict[str, str]:
    """Sign AWS request with credentials."""
    try:
        access_key, secret_key, session_token = _get_aws_credentials(cache, http_client)

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


def _create_auth_provider(
    auth: Optional[str] = None, http_client: Optional[ProductionHTTPClient] = None
):
    """Create authentication provider - returns a simple object with get_headers method."""
    if http_client is None:
        http_client = ProductionHTTPClient()

    class AuthProvider:
        def __init__(
            self,
            auth_type: str,
            auth_value: Optional[str] = None,
            http_client: ProductionHTTPClient = None,
        ):
            self.auth_type = auth_type
            self.auth_value = auth_value
            self._token_cache = {}
            self._http_client = http_client

        def get_headers(self) -> Dict[str, str]:
            if self.auth_type == "none":
                return {}
            elif self.auth_type == "bearer":
                return {"Authorization": f"Bearer {self.auth_value}"}
            elif self.auth_type == "gcp":
                token = _get_gcp_token(
                    cache=self._token_cache,
                    http_client=self._http_client,
                    service_account_path=self.auth_value,
                )
                return {"Authorization": f"Bearer {token}"}
            elif self.auth_type == "azure":
                token = _get_azure_token(
                    cache=self._token_cache, http_client=self._http_client
                )
                return {"Authorization": f"Bearer {token}"}
            elif self.auth_type == "aws":
                # AWS requires per-request signing, return signal to client
                return {
                    "X-AWS-Auth": "true"
                }  # Signal to client that AWS signing is needed

        def get_cache(self) -> Dict:
            """Get the token cache for this auth provider instance."""
            return self._token_cache

    if auth is None:
        # Auto-detect
        cloud_env = _detect_cloud_environment(http_client)
        if cloud_env == "gcp":
            return AuthProvider("gcp", http_client=http_client)
        elif cloud_env == "azure":
            return AuthProvider("azure", http_client=http_client)
        elif cloud_env == "aws":
            return AuthProvider("aws", http_client=http_client)
        else:
            return AuthProvider("none", http_client=http_client)

    elif isinstance(auth, str):
        # Check if it's a file path (GCP service account)
        if auth.endswith(".json") and os.path.exists(auth):
            return AuthProvider("gcp", auth, http_client=http_client)
        else:
            # Assume it's a bearer token
            return AuthProvider("bearer", auth, http_client=http_client)
