import warnings

import yaml

from pgmonkey.common.utils.envutils import resolve_env_vars


def load_config(file_path, resolve_env=False, allow_sensitive_defaults=False):
    """Load and optionally interpolate a pgmonkey YAML configuration file.

    This is the recommended entry point for programmatic config loading.

    Parameters
    ----------
    file_path : str
        Path to the YAML configuration file.
    resolve_env : bool
        If True, ``${VAR}`` / ``${VAR:-default}`` patterns and
        ``from_env`` / ``from_file`` structured references are resolved.
    allow_sensitive_defaults : bool
        If True, ``${VAR:-default}`` is permitted even for sensitive keys
        like ``password``.  Default is False for safety.

    Returns
    -------
    dict
        The parsed (and optionally resolved) configuration dictionary.
    """
    with open(file_path, 'r') as f:
        config = yaml.safe_load(f)

    config = normalize_config(config)

    if resolve_env:
        config = resolve_env_vars(
            config,
            allow_sensitive_defaults=allow_sensitive_defaults,
        )

    return config


def normalize_config(config_data):
    """Normalize a pgmonkey configuration dictionary.

    In pgmonkey v3.0.0, the top-level 'postgresql:' wrapper key was removed.
    This function detects the old format and unwraps it with a deprecation warning.

    Args:
        config_data: Configuration dictionary (old or new format).

    Returns:
        The normalized configuration dictionary (without the 'postgresql:' wrapper).
    """
    if isinstance(config_data, dict) and 'postgresql' in config_data:
        warnings.warn(
            "The top-level 'postgresql:' key in pgmonkey config files is deprecated "
            "since v3.0.0 and will be removed in a future version. "
            "Remove the 'postgresql:' wrapper and dedent all settings one level. "
            "See https://pgmonkey.net/reference.html for the new format.",
            DeprecationWarning,
            stacklevel=3,
        )
        return config_data['postgresql']
    return config_data
