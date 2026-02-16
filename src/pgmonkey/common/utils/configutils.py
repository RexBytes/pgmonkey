import warnings


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
