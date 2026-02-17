"""Redaction utilities for pgmonkey config values.

Masks sensitive values (passwords, keys, tokens) so they can be safely
printed in logs, CLI output, and error messages.
"""

import copy

from pgmonkey.common.utils.envutils import SENSITIVE_KEYS, _SENSITIVE_SUBSTRINGS

REDACTED = '***REDACTED***'


def _should_redact(key):
    """Return True if *key* names a sensitive config value."""
    lower = key.lower()
    if lower in SENSITIVE_KEYS:
        return True
    return any(sub in lower for sub in _SENSITIVE_SUBSTRINGS)


def redact_config(config):
    """Return a deep copy of *config* with sensitive values replaced.

    Non-empty sensitive values are replaced with ``'***REDACTED***'``.
    Empty strings and None are left as-is (nothing to leak).

    Parameters
    ----------
    config : dict
        The resolved config dictionary.

    Returns
    -------
    dict
        A new dictionary safe for printing/logging.
    """
    if not isinstance(config, dict):
        return config

    result = {}
    for key, value in config.items():
        if isinstance(value, dict):
            result[key] = redact_config(value)
        elif _should_redact(key) and value:
            result[key] = REDACTED
        else:
            result[key] = copy.deepcopy(value) if isinstance(value, (dict, list)) else value
    return result
