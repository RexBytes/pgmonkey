from importlib.metadata import version, PackageNotFoundError


class ToplevelManager:
    @staticmethod
    def get_package_version(package_name: str) -> str:
        """Fetch the package version using the package name."""
        try:
            return version(package_name)
        except PackageNotFoundError:
            return "Package version not found"

    # You can add more top-level management methods here
