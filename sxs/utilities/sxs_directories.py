import functools


def read_config(key=None, default=None):
    """Read variable from SXS configuration file

    The configuration file is named `config.json` and is stored in the directory
    returned by `sxs_directory("config")`.

    Parameters
    ----------
    key : {None, str}
        If None (the default), the entire configuration file is returned as a
        dictionary.  Otherwise, this is used as a key for this dictionary.
    default : Any
        An arbitrary object that is returned if the `key` is not found in the
        dictionary.

    Returns
    -------
    config : {dict, Any}
        If `key` is None (the default), the entire configuration dictionary is
        returned.  Otherwise, the value indexed by that key in the configuration
        file is returned.

    """
    import json
    config_path = sxs_directory("config") / "config.json"
    if config_path.exists():
        config = json.load(config_path)
    else:
        config = {}
    if key is None:
        return config
    else:
        return config.get(key, default)


def write_config(**kwargs):
    """Write variables to SXS configuration file

    The configuration file is named `config.json` and is stored in the directory
    returned by `sxs_directory("config")`.

    All parameters must be passed as keyword arguments, as in

        write_config(key=value)

    which are then inserted as `key:value` pairs into the config dictionary and
    written into the `config.json` file.

    """
    import json
    config_path = sxs_directory("config") / "config.json"
    if config_path.exists():
        config = json.load(config_path)
    else:
        config = {}
    config.update(**kwargs)
    with config.open("w") as c:
        json.dump(config, c, indent=4, separators=(',', ': '))


@functools.lru_cache()
def sxs_directory(directory_type, persistent=True):
    """Return the SXS directory location, creating it if necessary

    Parameters
    ----------
    directory_type : {"cache", "config"}
        The type of user directory to be found.
    persistent : bool
        If True (the default) try to return a persistent directory; otherwise,
        return a temporary directory that will be deleted when the calling python
        process exits (via the standard-libary function `atexit.register`).

    Returns
    -------
    directory : pathlib.Path
        The full path to the config or cache directory.  The directory is created
        if it does not exist, and it is checked to make sure it can be written to.

    Notes
    -----
    In order of priority, this function will choose one of these directories:

      1) Environment variable 'SXSCACHEDIR' or 'SXSCONFIGDIR'
      2) On 'linux' or 'freebsd' platforms
         a) Environment variable 'XDG_CACHE_HOME' or 'XDG_CONFIG_HOME'
         b) The '.cache/sxs' or '.config/sxs' directory in the user's home directory
      3) The '.sxs' directory in the user's home directory

    Whichever directory is chosen, this function will try to create the directory
    if necessary, and then check that it can be accessed and written to.  If that
    check fails, the function will create and return

      4) A temporary directory that will be removed when python exits

    This is based on matplotlib's _get_config_or_cache_dir function.

    """
    import warnings
    import sys
    import os
    import atexit
    import shutil
    import tempfile
    from pathlib import Path

    if directory_type not in ["cache", "config"]:
        raise ValueError(f"Can only find 'cache' or 'config' directories, not '{directory_type}'")

    suffix = Path("cache") if directory_type == "cache" else Path()

    if persistent:
        sxs_dir = os.getenv(f'SXS{directory_type.upper()}DIR', default=False)

        if sxs_dir:
            sxs_dir = Path(sxs_dir).expanduser().resolve()
        elif sys.platform.startswith(('linux', 'freebsd')):  # pragma: no cover
            xdg_base = os.environ.get(f'XDG_{directory_type.upper()}_HOME') or Path.home() / f".{directory_type}"
            sxs_dir = Path(xdg_base).expanduser().resolve() / "sxs"
        else:
            sxs_dir = Path.home() / ".sxs" / suffix

        try:
            sxs_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        else:
            if os.access(str(sxs_dir), os.W_OK) and sxs_dir.is_dir():
                return sxs_dir

        unwritable_dir = sxs_dir

    # We've fallen through to creating a temporary directory.  We want the cache directory to be a
    # subdirectory of the main directory, so we fetch it through the lru_cache.  We can't do this
    # above, because it should be possible to get different results for certain settings.
    if directory_type == "cache":
        sxs_dir = sxs_directory("config", persistent=persistent) / "cache"
        try:
            sxs_dir.mkdir(exist_ok=True)
        except OSError:  # pragma: no cover
            pass
        else:
            if os.access(str(sxs_dir), os.W_OK) and sxs_dir.is_dir():  # pragma: no cover
                return sxs_dir

    # If the config or cache directory cannot be created or is not a writable
    # directory, create a temporary one.
    tmpdir = os.environ[f'SXS{directory_type.upper()}DIR'] = tempfile.mkdtemp(prefix="sxs-")
    atexit.register(shutil.rmtree, tmpdir)
    sxs_dir = Path(tmpdir) / suffix
    if persistent:
        message = (
            f"\nThe `sxs` module created a temporary {directory_type} directory at {sxs_dir}\n"
            f"because the default path ({unwritable_dir}) is not a writable directory;\n"
            f"it is highly recommended to set the SXS{directory_type.upper()}DIR environment\n"
            f"variable to a writable directory to enable caching of downloaded waveforms."
        )
        warnings.warn(message)
    if directory_type == "cache":  # pragma: no cover
        sxs_dir.mkdir(exist_ok=True)
    return sxs_dir