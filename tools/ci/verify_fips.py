# verify_fips.py — Check OpenSSL FIPS 140-3 mode.
# Stdlib-only. Exit 0 on pass, exit 1 on failure.
#
# Two-tier check:
#   1. Primary: `openssl list -providers` — look for active FIPS provider (OpenSSL 3.x)
#   2. Fallback: `openssl version` — check for "fips" in version string (OpenSSL 1.x / LibreSSL)

import subprocess
import sys

TIMEOUT = 10  # seconds


def check_fips_provider():
    """Primary check: OpenSSL 3.x FIPS provider.

    Returns:
        True  — FIPS provider found and active
        False — provider list parsed but FIPS not active
        None  — command not supported (fall through to fallback)
    """
    try:
        out = subprocess.check_output(
            ["openssl", "list", "-providers"],
            text=True,
            timeout=TIMEOUT,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        print("FAIL: openssl not found on PATH.")
        sys.exit(1)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        # OpenSSL 1.x / LibreSSL doesn't support `list -providers`
        return None

    # Parse provider output. Format:
    #   Providers:
    #     fips
    #       name: OpenSSL FIPS Provider
    #       ...
    #       status: active
    in_fips_block = False
    for line in out.splitlines():
        stripped = line.strip().lower()
        # Provider ID line (indented, no colon — e.g. "  fips")
        if stripped == "fips":
            in_fips_block = True
            continue
        # If we hit another provider ID (no colon, not empty), leave fips block
        if in_fips_block and stripped and ":" not in stripped:
            in_fips_block = False
        # Check for active status within the fips block
        if in_fips_block and stripped == "status: active":
            return True

    return False


def check_fips_version():
    """Fallback check: `openssl version` string contains 'fips'.

    Returns:
        True  — 'fips' found in version string
        False — not found or command failed
    """
    try:
        out = subprocess.check_output(
            ["openssl", "version"],
            text=True,
            timeout=TIMEOUT,
            stderr=subprocess.DEVNULL,
        )
        return "fips" in out.lower()
    except FileNotFoundError:
        print("FAIL: openssl not found on PATH.")
        sys.exit(1)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def main():
    # Tier 1: Provider check (OpenSSL 3.x)
    provider_result = check_fips_provider()
    if provider_result is True:
        print("OK: FIPS provider active (openssl list -providers).")
        return 0
    if provider_result is False:
        print("FAIL: OpenSSL FIPS provider not active.")
        return 1

    # Tier 2: Version string fallback (OpenSSL 1.x / LibreSSL)
    if check_fips_version():
        print("OK: FIPS-capable build detected (fallback: version string contains 'fips').")
        return 0

    print("FAIL: OpenSSL not in FIPS mode or not FIPS build.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
