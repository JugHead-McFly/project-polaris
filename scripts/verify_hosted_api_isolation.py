#!/usr/bin/env python3
"""Exercise hosted API tenant isolation with a temporary Supabase user.

Required environment variables:

POLARIS_SUPABASE_URL
POLARIS_SUPABASE_PUBLISHABLE_KEY
POLARIS_PROTECTED_USER_ID
POLARIS_PROTECTED_OBSERVATORY_ID

Supply the temporary account through either:

POLARIS_ISOLATION_CREDENTIAL_FILE

or:

POLARIS_ISOLATION_TEST_EMAIL
POLARIS_ISOLATION_TEST_PASSWORD

The script never prints credentials or access tokens. It creates and removes
one observatory owned by the temporary user. The temporary profile and
Supabase Auth user are intentionally left for the caller to remove together
after the rehearsal.
"""

import json
import os
import sys
from typing import Dict
from typing import Optional
from urllib import error
from urllib import parse
from urllib import request


DEFAULT_API_BASE_URL = "http://127.0.0.1:8001"
TEST_OBSERVATORY_NAME = "Polaris isolation rehearsal"


class RehearsalError(RuntimeError):
    """Raised when a hosted isolation expectation is not met."""


def require_environment(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RehearsalError(f"Required environment variable is missing: {name}")
    return value


def test_credentials() -> tuple:
    credential_file = os.getenv(
        "POLARIS_ISOLATION_CREDENTIAL_FILE",
        "",
    ).strip()
    if credential_file:
        try:
            with open(credential_file, encoding="utf-8") as handle:
                credentials = json.load(handle)
        except (OSError, json.JSONDecodeError) as credential_error:
            raise RehearsalError(
                "The temporary credential file could not be read."
            ) from credential_error
        email = str(credentials.get("email", "")).strip()
        password = str(credentials.get("password", ""))
        if not email or not password:
            raise RehearsalError(
                "The temporary credential file is incomplete."
            )
        return email, password

    return (
        require_environment("POLARIS_ISOLATION_TEST_EMAIL"),
        require_environment("POLARIS_ISOLATION_TEST_PASSWORD"),
    )


def request_json(
    url: str,
    *,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    payload: Optional[Dict] = None,
) -> tuple:
    request_headers = {
        "Accept": "application/json",
        **(headers or {}),
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    api_request = request.Request(
        url,
        data=data,
        headers=request_headers,
        method=method,
    )
    try:
        with request.urlopen(api_request, timeout=15) as response:
            body = response.read()
            decoded = json.loads(body) if body else None
            return response.status, decoded
    except error.HTTPError as http_error:
        body = http_error.read()
        try:
            decoded = json.loads(body) if body else None
        except json.JSONDecodeError:
            decoded = None
        return http_error.code, decoded
    except error.URLError as network_error:
        raise RehearsalError(
            f"Could not reach {parse.urlsplit(url).netloc}."
        ) from network_error


def expect_status(
    label: str,
    actual_status: int,
    expected_status: int,
) -> None:
    if actual_status != expected_status:
        raise RehearsalError(
            f"{label}: expected HTTP {expected_status}, got {actual_status}."
        )
    print(f"PASS: {label}")


def access_token(
    *,
    supabase_url: str,
    publishable_key: str,
    email: str,
    password: str,
) -> str:
    status, response = request_json(
        (
            f"{supabase_url.rstrip('/')}/auth/v1/token"
            "?grant_type=password"
        ),
        method="POST",
        headers={"apikey": publishable_key},
        payload={
            "email": email,
            "password": password,
        },
    )
    expect_status("temporary user authentication", status, 200)
    token = (response or {}).get("access_token")
    if not token:
        raise RehearsalError(
            "Supabase authenticated the user but returned no access token."
        )
    return token


def main() -> int:
    supabase_url = require_environment("POLARIS_SUPABASE_URL")
    publishable_key = require_environment(
        "POLARIS_SUPABASE_PUBLISHABLE_KEY"
    )
    test_email, test_password = test_credentials()
    protected_user_id = require_environment("POLARIS_PROTECTED_USER_ID")
    protected_observatory_id = require_environment(
        "POLARIS_PROTECTED_OBSERVATORY_ID"
    )
    api_base_url = os.getenv(
        "POLARIS_ISOLATION_API_BASE_URL",
        DEFAULT_API_BASE_URL,
    ).rstrip("/")

    token = access_token(
        supabase_url=supabase_url,
        publishable_key=publishable_key,
        email=test_email,
        password=test_password,
    )
    auth_headers = {"Authorization": f"Bearer {token}"}

    status, identity = request_json(
        f"{api_base_url}/auth/me",
        headers=auth_headers,
    )
    expect_status("authenticated identity", status, 200)
    test_user_id = (identity or {}).get("user_id")
    if not test_user_id or test_user_id == protected_user_id:
        raise RehearsalError(
            "The temporary user is missing or matches the protected owner."
        )
    print("PASS: temporary user is a separate account")

    status, _ = request_json(
        f"{api_base_url}/profile",
        method="PUT",
        headers=auth_headers,
        payload={
            "display_name": "Polaris isolation test",
            "onboarding_state": "security_rehearsal",
        },
    )
    expect_status("temporary profile creation", status, 200)

    status, observatories = request_json(
        f"{api_base_url}/observatories",
        headers=auth_headers,
    )
    expect_status("temporary user observatory list", status, 200)
    if any(
        item.get("id") == protected_observatory_id
        for item in (observatories or [])
    ):
        raise RehearsalError(
            "The protected observatory appeared in the temporary user's list."
        )
    print("PASS: protected observatory is absent from list results")

    protected_url = (
        f"{api_base_url}/observatories/{protected_observatory_id}"
    )
    status, _ = request_json(
        protected_url,
        headers=auth_headers,
    )
    expect_status("cross-owner direct read is hidden", status, 404)

    status, _ = request_json(
        protected_url,
        method="PATCH",
        headers=auth_headers,
        payload={"name": "Unauthorized change"},
    )
    expect_status("cross-owner update is blocked", status, 404)

    status, _ = request_json(
        protected_url,
        method="DELETE",
        headers=auth_headers,
    )
    expect_status("cross-owner deletion is blocked", status, 404)

    base_observatory = {
        "name": TEST_OBSERVATORY_NAME,
        "latitude": 33.25,
        "longitude": -111.75,
        "coordinates_are_approximate": True,
        "elevation_m": 390,
        "timezone_name": "America/Phoenix",
        "bortle_class": 6,
    }
    status, _ = request_json(
        f"{api_base_url}/observatories",
        method="POST",
        headers=auth_headers,
        payload={
            **base_observatory,
            "user_id": protected_user_id,
        },
    )
    expect_status("forged owner field is rejected", status, 422)

    test_observatory_id = None
    try:
        status, created = request_json(
            f"{api_base_url}/observatories",
            method="POST",
            headers=auth_headers,
            payload=base_observatory,
        )
        expect_status("temporary user creates own observatory", status, 201)
        test_observatory_id = (created or {}).get("id")
        if not test_observatory_id:
            raise RehearsalError(
                "The temporary observatory response had no record ID."
            )

        status, own_record = request_json(
            f"{api_base_url}/observatories/{test_observatory_id}",
            headers=auth_headers,
        )
        expect_status("temporary user reads own observatory", status, 200)
        if (own_record or {}).get("id") != test_observatory_id:
            raise RehearsalError(
                "The temporary user's own observatory was not returned."
            )

        status, _ = request_json(
            f"{api_base_url}/observatories/{test_observatory_id}",
            method="PATCH",
            headers=auth_headers,
            payload={"name": f"{TEST_OBSERVATORY_NAME} updated"},
        )
        expect_status("temporary user updates own observatory", status, 200)
    finally:
        if test_observatory_id:
            cleanup_status, _ = request_json(
                f"{api_base_url}/observatories/{test_observatory_id}",
                method="DELETE",
                headers=auth_headers,
            )
            expect_status(
                "temporary observatory cleanup",
                cleanup_status,
                204,
            )

    print("PASS: hosted API tenant-isolation rehearsal completed")
    print(f"TEST_USER_ID={test_user_id}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RehearsalError as rehearsal_error:
        print(f"FAIL: {rehearsal_error}", file=sys.stderr)
        raise SystemExit(1)
