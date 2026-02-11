"""
KIS (Korea Investment & Securities) OAuth API Functions.

This module provides functions for OAuth authentication with the KIS OpenAPI,
including token issuance, token revocation, hash key generation, and WebSocket
approval key generation.

API Reference: https://apiportal.koreainvestment.com/
"""

import httpx
from typing import Any, Dict, Literal

# URL constants for reference
KIS_BASE_URL_REAL = "https://openapi.koreainvestment.com:9443"
KIS_BASE_URL_PAPER = "https://openapivts.koreainvestment.com:29443"

# OAuth endpoint paths
OAUTH_TOKEN_PATH = "/oauth2/tokenP"
OAUTH_REVOKE_PATH = "/oauth2/revokeP"
HASH_KEY_PATH = "/uapi/hashkey"
WEBSOCKET_APPROVAL_PATH = "/oauth2/Approval"


def issue_access_token(
    app_key: str,
    app_secret: str,
    is_paper_trading: bool = True,
    custtype: Literal["P", "B"] = "P",
) -> Dict[str, Any]:
    """
    Issue an OAuth access token for KIS OpenAPI authentication.

    This function requests a new access token from the KIS OpenAPI server.
    The access token is required for all subsequent API calls.

    Args:
        app_key: KIS OpenAPI application key issued from the portal.
        app_secret: KIS OpenAPI application secret issued from the portal.
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Defaults to True for paper trading environment.
        custtype: Customer type. 'P' for individual, 'B' for corporate.
            Defaults to 'P' (individual).

    Returns:
        Dict[str, Any]: API response containing:
            - rt_cd (str): Return code ('0' for success, '1' for failure)
            - msg_cd (str): Message code
            - msg1 (str): Message description
            - access_token (str): OAuth access token (on success)
            - token_type (str): Token type (usually 'Bearer')
            - expires_in (int): Token expiration time in seconds (usually 86400/24 hours)

    Raises:
        ValueError: If required parameters are invalid.
        httpx.HTTPError: If connection to KIS API fails.

    Examples:
        >>> response = issue_access_token(
        ...     app_key="your_app_key",
        ...     app_secret="your_app_secret",
        ...     is_paper_trading=True
        ... )
        >>> if response.get("rt_cd") == "0":
        ...     token = response.get("access_token")
        ...     print(f"Access token: {token}")

    Notes:
        - Access tokens are valid for 24 hours (86400 seconds)
        - Store access tokens securely and refresh before expiration
        - Paper trading URL: https://openapivts.koreainvestment.com:29443/oauth2/tokenP
        - Real trading URL: https://openapi.koreainvestment.com:9443/oauth2/tokenP
    """
    url = get_oauth_url(OAUTH_TOKEN_PATH, is_paper_trading)

    headers = {
        "Content-Type": "application/json",
        "appkey": app_key,
        "appsecret": app_secret,
        "custtype": custtype,
    }

    data = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret,
    }

    response = httpx.post(url, json=data, headers=headers, timeout=30.0)
    response.raise_for_status()

    return response.json()


def issue_access_token_real(
    app_key: str,
    app_secret: str,
    custtype: Literal["P", "B"] = "P",
) -> Dict[str, Any]:
    """
    Issue an OAuth access token for real trading environment.

    Convenience function that calls issue_access_token with is_paper_trading=False.

    Args:
        app_key: KIS OpenAPI application key issued from the portal.
        app_secret: KIS OpenAPI application secret issued from the portal.
        custtype: Customer type. 'P' for individual, 'B' for corporate.
            Defaults to 'P' (individual).

    Returns:
        Dict[str, Any]: API response with access token information.

    Examples:
        >>> response = issue_access_token_real(
        ...     app_key="your_app_key",
        ...     app_secret="your_app_secret"
        ... )
        >>> token = response.get("access_token")

    Notes:
        - Real trading URL: https://openapi.koreainvestment.com:9443/oauth2/tokenP
        - Use this for production/real trading operations
    """
    return issue_access_token(
        app_key=app_key,
        app_secret=app_secret,
        is_paper_trading=False,
        custtype=custtype,
    )


def issue_access_token_paper(
    app_key: str,
    app_secret: str,
    custtype: Literal["P", "B"] = "P",
) -> Dict[str, Any]:
    """
    Issue an OAuth access token for paper trading environment.

    Convenience function that calls issue_access_token with is_paper_trading=True.

    Args:
        app_key: KIS OpenAPI application key issued from the portal.
        app_secret: KIS OpenAPI application secret issued from the portal.
        custtype: Customer type. 'P' for individual, 'B' for corporate.
            Defaults to 'P' (individual).

    Returns:
        Dict[str, Any]: API response with access token information.

    Examples:
        >>> response = issue_access_token_paper(
        ...     app_key="your_app_key",
        ...     app_secret="your_app_secret"
        ... )
        >>> token = response.get("access_token")

    Notes:
        - Paper trading URL: https://openapivts.koreainvestment.com:29443/oauth2/tokenP
        - Use this for testing and development
    """
    return issue_access_token(
        app_key=app_key,
        app_secret=app_secret,
        is_paper_trading=True,
        custtype=custtype,
    )


def revoke_access_token(
    app_key: str,
    app_secret: str,
    access_token: str,
    is_paper_trading: bool = True,
    custtype: Literal["P", "B"] = "P",
) -> Dict[str, Any]:
    """
    Revoke an OAuth access token.

    This function invalidates the specified access token, making it unusable
    for future API calls. Use this when logging out or when a token is no
    longer needed.

    Args:
        app_key: KIS OpenAPI application key issued from the portal.
        app_secret: KIS OpenAPI application secret issued from the portal.
        access_token: The access token to revoke.
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Defaults to True for paper trading environment.
        custtype: Customer type. 'P' for individual, 'B' for corporate.
            Defaults to 'P' (individual).

    Returns:
        Dict[str, Any]: API response containing:
            - rt_cd (str): Return code ('0' for success, '1' for failure)
            - msg_cd (str): Message code
            - msg1 (str): Message description

    Raises:
        ValueError: If required parameters are invalid.
        httpx.HTTPError: If connection to KIS API fails.

    Examples:
        >>> response = revoke_access_token(
        ...     app_key="your_app_key",
        ...     app_secret="your_app_secret",
        ...     access_token="old_token_to_revoke",
        ...     is_paper_trading=True
        ... )
        >>> if response.get("rt_cd") == "0":
        ...     print("Token revoked successfully")

    Notes:
        - Paper trading URL: https://openapivts.koreainvestment.com:29443/oauth2/revokeP
        - Real trading URL: https://openapi.koreainvestment.com:9443/oauth2/revokeP
        - After revocation, obtain a new access token for subsequent API calls
    """
    url = get_oauth_url(OAUTH_REVOKE_PATH, is_paper_trading)

    headers = {
        "Content-Type": "application/json",
        "appkey": app_key,
        "appsecret": app_secret,
        "custtype": custtype,
    }

    data = {
        "token": access_token,
    }

    response = httpx.post(url, json=data, headers=headers, timeout=30.0)
    response.raise_for_status()

    return response.json()


def revoke_access_token_real(
    app_key: str,
    app_secret: str,
    access_token: str,
    custtype: Literal["P", "B"] = "P",
) -> Dict[str, Any]:
    """
    Revoke an OAuth access token for real trading environment.

    Convenience function that calls revoke_access_token with is_paper_trading=False.

    Args:
        app_key: KIS OpenAPI application key issued from the portal.
        app_secret: KIS OpenAPI application secret issued from the portal.
        access_token: The access token to revoke.
        custtype: Customer type. 'P' for individual, 'B' for corporate.
            Defaults to 'P' (individual).

    Returns:
        Dict[str, Any]: API response indicating revocation status.

    Examples:
        >>> response = revoke_access_token_real(
        ...     app_key="your_app_key",
        ...     app_secret="your_app_secret",
        ...     access_token="old_token"
        ... )
        >>> if response.get("rt_cd") == "0":
        ...     print("Token revoked successfully")
    """
    return revoke_access_token(
        app_key=app_key,
        app_secret=app_secret,
        access_token=access_token,
        is_paper_trading=False,
        custtype=custtype,
    )


def revoke_access_token_paper(
    app_key: str,
    app_secret: str,
    access_token: str,
    custtype: Literal["P", "B"] = "P",
) -> Dict[str, Any]:
    """
    Revoke an OAuth access token for paper trading environment.

    Convenience function that calls revoke_access_token with is_paper_trading=True.

    Args:
        app_key: KIS OpenAPI application key issued from the portal.
        app_secret: KIS OpenAPI application secret issued from the portal.
        access_token: The access token to revoke.
        custtype: Customer type. 'P' for individual, 'B' for corporate.
            Defaults to 'P' (individual).

    Returns:
        Dict[str, Any]: API response indicating revocation status.

    Examples:
        >>> response = revoke_access_token_paper(
        ...     app_key="your_app_key",
        ...     app_secret="your_app_secret",
        ...     access_token="old_token"
        ... )
        >>> if response.get("rt_cd") == "0":
        ...     print("Token revoked successfully")
    """
    return revoke_access_token(
        app_key=app_key,
        app_secret=app_secret,
        access_token=access_token,
        is_paper_trading=True,
        custtype=custtype,
    )


def generate_hash_key(
    app_key: str,
    app_secret: str,
    payload: Dict[str, Any],
    is_paper_trading: bool = True,
) -> str:
    """
    Generate a hash key for POST request body encryption.

    This function generates a SHA-512 hash key that is required for POST
    requests to certain KIS OpenAPI endpoints. The hash key is computed
    from the request payload and is used for data integrity verification.

    Args:
        app_key: KIS OpenAPI application key issued from the portal.
        app_secret: KIS OpenAPI application secret issued from the portal.
        payload: The request body data (as a dictionary) to be hashed.
            The payload will be converted to a JSON string for hashing.
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Defaults to True for paper trading environment.

    Returns:
        str: The base64-encoded hash key string to be included in the
            'hash' header of POST requests.

    Raises:
        ValueError: If required parameters are invalid or payload is empty.
        httpx.HTTPError: If connection to KIS API fails.

    Examples:
        >>> payload = {"symbol": "005930", "qty": 10}
        >>> hash_key = generate_hash_key(
        ...     app_key="your_app_key",
        ...     app_secret="your_app_secret",
        ...     payload=payload,
        ...     is_paper_trading=True
        ... )
        >>> headers = {"hash": hash_key}

    Notes:
        - Paper trading URL: https://openapivts.koreainvestment.com:29443/uapi/hashkey
        - Real trading URL: https://openapi.koreainvestment.com:9443/uapi/hashkey
        - The hash key is computed as: base64(SHA-512(app_secret + ASCII(payload)))
        - Some POST APIs require the hash key in the request header
        - The returned format is: {"hash": "<base64_encoded_hash>"}
    """
    url = get_oauth_url(HASH_KEY_PATH, is_paper_trading)

    headers = {
        "Content-Type": "application/json",
        "appkey": app_key,
        "appsecret": app_secret,
    }

    # Convert payload to JSON string for the request body
    data = payload

    response = httpx.post(url, json=data, headers=headers, timeout=30.0)
    response.raise_for_status()

    result = response.json()
    return result.get("hash", "")


def generate_hash_key_real(
    app_key: str,
    app_secret: str,
    payload: Dict[str, Any],
) -> str:
    """
    Generate a hash key for real trading environment.

    Convenience function that calls generate_hash_key with is_paper_trading=False.

    Args:
        app_key: KIS OpenAPI application key issued from the portal.
        app_secret: KIS OpenAPI application secret issued from the portal.
        payload: The request body data (as a dictionary) to be hashed.

    Returns:
        str: The base64-encoded hash key string.

    Examples:
        >>> payload = {"symbol": "005930", "qty": 10}
        >>> hash_key = generate_hash_key_real(
        ...     app_key="your_app_key",
        ...     app_secret="your_app_secret",
        ...     payload=payload
        ... )
        >>> headers = {"hash": hash_key}
    """
    return generate_hash_key(
        app_key=app_key,
        app_secret=app_secret,
        payload=payload,
        is_paper_trading=False,
    )


def generate_hash_key_paper(
    app_key: str,
    app_secret: str,
    payload: Dict[str, Any],
) -> str:
    """
    Generate a hash key for paper trading environment.

    Convenience function that calls generate_hash_key with is_paper_trading=True.

    Args:
        app_key: KIS OpenAPI application key issued from the portal.
        app_secret: KIS OpenAPI application secret issued from the portal.
        payload: The request body data (as a dictionary) to be hashed.

    Returns:
        str: The base64-encoded hash key string.

    Examples:
        >>> payload = {"symbol": "005930", "qty": 10}
        >>> hash_key = generate_hash_key_paper(
        ...     app_key="your_app_key",
        ...     app_secret="your_app_secret",
        ...     payload=payload
        ... )
        >>> headers = {"hash": hash_key}
    """
    return generate_hash_key(
        app_key=app_key,
        app_secret=app_secret,
        payload=payload,
        is_paper_trading=True,
    )


def approve_websocket_key(
    app_key: str,
    app_secret: str,
    access_token: str,
    is_paper_trading: bool = True,
    custtype: Literal["P", "B"] = "P",
) -> Dict[str, Any]:
    """
    Generate an approval key for WebSocket connection.

    This function requests an approval key required for establishing a WebSocket
    connection to receive real-time market data. The approval key is valid for
    a limited time and must be included in the WebSocket handshake.

    Args:
        app_key: KIS OpenAPI application key issued from the portal.
        app_secret: KIS OpenAPI application secret issued from the portal.
        access_token: Valid OAuth access token for authentication.
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Defaults to True for paper trading environment.
        custtype: Customer type. 'P' for individual, 'B' for corporate.
            Defaults to 'P' (individual).

    Returns:
        Dict[str, Any]: API response containing:
            - rt_cd (str): Return code ('0' for success, '1' for failure)
            - msg_cd (str): Message code
            - msg1 (str): Message description
            - approval_key (str): WebSocket approval key (on success)
            - token_type (str): Token type (usually 'Bearer')

    Raises:
        ValueError: If required parameters are invalid.
        httpx.HTTPError: If connection to KIS API fails.

    Examples:
        >>> response = approve_websocket_key(
        ...     app_key="your_app_key",
        ...     app_secret="your_app_secret",
        ...     access_token="your_access_token",
        ...     is_paper_trading=True
        ... )
        >>> if response.get("rt_cd") == "0":
        ...     ws_key = response.get("approval_key")
        ...     # Use ws_key for WebSocket connection

    Notes:
        - Paper trading URL: https://openapivts.koreainvestment.com:29443/oauth2/Approval
        - Real trading URL: https://openapi.koreainvestment.com:9443/oauth2/Approval
        - The approval key has a limited validity period
        - A new approval key is required for each WebSocket connection
        - Real-time data WebSocket URL format: ws://<server>/oauth2/socket
    """
    url = get_oauth_url(WEBSOCKET_APPROVAL_PATH, is_paper_trading)

    headers = {
        "Content-Type": "application/json",
        "appkey": app_key,
        "appsecret": app_secret,
        "Authorization": f"Bearer {access_token}",
        "custtype": custtype,
    }

    data = {}

    response = httpx.post(url, json=data, headers=headers, timeout=30.0)
    response.raise_for_status()

    return response.json()


def approve_websocket_key_real(
    app_key: str,
    app_secret: str,
    access_token: str,
    custtype: Literal["P", "B"] = "P",
) -> Dict[str, Any]:
    """
    Generate an approval key for WebSocket connection in real trading environment.

    Convenience function that calls approve_websocket_key with is_paper_trading=False.

    Args:
        app_key: KIS OpenAPI application key issued from the portal.
        app_secret: KIS OpenAPI application secret issued from the portal.
        access_token: Valid OAuth access token for authentication.
        custtype: Customer type. 'P' for individual, 'B' for corporate.
            Defaults to 'P' (individual).

    Returns:
        Dict[str, Any]: API response with approval key.

    Examples:
        >>> response = approve_websocket_key_real(
        ...     app_key="your_app_key",
        ...     app_secret="your_app_secret",
        ...     access_token="your_access_token"
        ... )
        >>> ws_key = response.get("approval_key")
    """
    return approve_websocket_key(
        app_key=app_key,
        app_secret=app_secret,
        access_token=access_token,
        is_paper_trading=False,
        custtype=custtype,
    )


def approve_websocket_key_paper(
    app_key: str,
    app_secret: str,
    access_token: str,
    custtype: Literal["P", "B"] = "P",
) -> Dict[str, Any]:
    """
    Generate an approval key for WebSocket connection in paper trading environment.

    Convenience function that calls approve_websocket_key with is_paper_trading=True.

    Args:
        app_key: KIS OpenAPI application key issued from the portal.
        app_secret: KIS OpenAPI application secret issued from the portal.
        access_token: Valid OAuth access token for authentication.
        custtype: Customer type. 'P' for individual, 'B' for corporate.
            Defaults to 'P' (individual).

    Returns:
        Dict[str, Any]: API response with approval key.

    Examples:
        >>> response = approve_websocket_key_paper(
        ...     app_key="your_app_key",
        ...     app_secret="your_app_secret",
        ...     access_token="your_access_token"
        ... )
        >>> ws_key = response.get("approval_key")
    """
    return approve_websocket_key(
        app_key=app_key,
        app_secret=app_secret,
        access_token=access_token,
        is_paper_trading=True,
        custtype=custtype,
    )


def get_oauth_url(
    path: str,
    is_paper_trading: bool = True,
) -> str:
    """
    Get the full URL for an OAuth endpoint.

    Args:
        path: The API path (e.g., '/oauth2/tokenP').
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Defaults to True for paper trading environment.

    Returns:
        str: The complete URL for the specified endpoint.

    Examples:
        >>> url = get_oauth_url("/oauth2/tokenP", is_paper_trading=True)
        >>> print(url)
        https://openapivts.koreainvestment.com:29443/oauth2/tokenP
    """
    base_url = KIS_BASE_URL_PAPER if is_paper_trading else KIS_BASE_URL_REAL
    return f"{base_url}{path}"
