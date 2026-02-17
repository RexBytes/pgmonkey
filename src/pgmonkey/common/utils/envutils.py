"""Environment variable and secret interpolation for pgmonkey YAML configs.

Supports two substitution forms:

1. Inline string interpolation: ``${VAR}`` and ``${VAR:-default}``
2. Structured references: ``from_env: VAR`` and ``from_file: /path/to/secret``

Interpolation is opt-in (disabled by default) and fails hard on missing
variables unless a default is provided.  Defaults are disallowed for
sensitive keys (password, sslkey, etc.) unless explicitly permitted.
"""

import os
import re
import logging

logger = logging.getLogger(__name__)

# Regex for ${VAR} and ${VAR:-default} inside strings.
# Captures:  group(1) = VAR name,  group(2) = default value (or None)
_ENV_PATTERN = re.compile(
    r'\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-(.*?))?\}'
)

# Keys whose values are considered secrets.  Defaults are disallowed for
# these keys unless the caller explicitly opts in.
SENSITIVE_KEYS = frozenset({
    'password',
    'sslkey',
    'sslcert',
    'sslrootcert',
})

# Substrings that mark a key as sensitive regardless of its exact name.
_SENSITIVE_SUBSTRINGS = ('token', 'secret', 'credential')


def _is_sensitive_key(key):
    """Return True if *key* is considered a sensitive config key."""
    lower = key.lower()
    if lower in SENSITIVE_KEYS:
        return True
    return any(sub in lower for sub in _SENSITIVE_SUBSTRINGS)


class EnvInterpolationError(Exception):
    """Raised when environment interpolation fails."""


def _resolve_env_var(var_name, default, key_path, allow_sensitive_defaults):
    """Resolve a single ``${VAR}`` or ``${VAR:-default}`` reference.

    Parameters
    ----------
    var_name : str
        Environment variable name.
    default : str or None
        Default value (None if not provided).
    key_path : str
        Dotted config key path for error messages (e.g. ``connection_settings.password``).
    allow_sensitive_defaults : bool
        If False, defaults for sensitive keys raise an error.

    Returns
    -------
    str
        The resolved value.
    """
    value = os.environ.get(var_name)
    if value is not None:
        return value

    if default is not None:
        if not allow_sensitive_defaults and _is_sensitive_key(key_path.rsplit('.', 1)[-1]):
            raise EnvInterpolationError(
                f"Default values are not allowed for sensitive key '{key_path}'. "
                f"Set the environment variable ${{{var_name}}} instead."
            )
        return default

    raise EnvInterpolationError(
        f"Environment variable '{var_name}' is not set and no default was "
        f"provided (referenced by config key '{key_path}')."
    )


def _interpolate_string(value, key_path, allow_sensitive_defaults):
    """Replace all ``${VAR}`` / ``${VAR:-default}`` patterns in *value*."""

    def _replacer(match):
        var_name = match.group(1)
        default = match.group(2)  # None when no :- was present
        return _resolve_env_var(var_name, default, key_path, allow_sensitive_defaults)

    return _ENV_PATTERN.sub(_replacer, value)


def _resolve_structured_ref(ref_dict, key_path):
    """Resolve a ``from_env`` or ``from_file`` structured reference.

    Parameters
    ----------
    ref_dict : dict
        A dict with exactly one key: ``from_env`` or ``from_file``.
    key_path : str
        Dotted config key path for error messages.

    Returns
    -------
    str
        The resolved secret value.
    """
    if 'from_env' in ref_dict:
        var_name = ref_dict['from_env']
        value = os.environ.get(var_name)
        if value is None:
            raise EnvInterpolationError(
                f"Environment variable '{var_name}' is not set "
                f"(referenced by config key '{key_path}' via from_env)."
            )
        return value

    if 'from_file' in ref_dict:
        file_path = ref_dict['from_file']
        try:
            with open(file_path, 'r') as f:
                # Trim trailing newline (Kubernetes Secret-style)
                return f.read().rstrip('\n')
        except FileNotFoundError:
            raise EnvInterpolationError(
                f"Secret file '{file_path}' not found "
                f"(referenced by config key '{key_path}' via from_file)."
            )
        except OSError as exc:
            raise EnvInterpolationError(
                f"Could not read secret file '{file_path}' "
                f"(referenced by config key '{key_path}' via from_file): {exc}"
            )

    return None  # Not a structured ref


def _is_structured_ref(value):
    """Return True if *value* looks like a from_env/from_file reference."""
    return (
        isinstance(value, dict)
        and len(value) == 1
        and next(iter(value)) in ('from_env', 'from_file')
    )


def resolve_env_vars(config, strict=False, allow_sensitive_defaults=False, _path=''):
    """Recursively resolve environment references in a config dictionary.

    Parameters
    ----------
    config : dict
        The parsed YAML config dictionary (will NOT be mutated; a new dict
        is returned).
    strict : bool
        If True, unknown top-level keys raise ``EnvInterpolationError``.
        (Currently reserved for future use.)
    allow_sensitive_defaults : bool
        If True, ``${VAR:-default}`` is allowed even for sensitive keys
        like ``password``.  Default is False for safety.

    Returns
    -------
    dict
        A new config dictionary with all env references resolved.

    Raises
    ------
    EnvInterpolationError
        If a referenced env var is missing (with no default), a secret file
        is unreadable, or a sensitive key has a disallowed default.
    """
    if not isinstance(config, dict):
        return config

    result = {}
    for key, value in config.items():
        current_path = f'{_path}.{key}' if _path else key

        if _is_structured_ref(value):
            result[key] = _resolve_structured_ref(value, current_path)

        elif isinstance(value, dict):
            result[key] = resolve_env_vars(
                value,
                strict=strict,
                allow_sensitive_defaults=allow_sensitive_defaults,
                _path=current_path,
            )

        elif isinstance(value, str) and '${' in value:
            result[key] = _interpolate_string(
                value, current_path, allow_sensitive_defaults,
            )

        elif isinstance(value, list):
            result[key] = [
                _interpolate_string(item, f'{current_path}[{i}]', allow_sensitive_defaults)
                if isinstance(item, str) and '${' in item
                else item
                for i, item in enumerate(value)
            ]

        else:
            result[key] = value

    return result
