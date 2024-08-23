import os
from pathlib import Path


class PathUtils:
    @staticmethod
    def construct_path(path_elements):
        """Construct a path from a list of elements, handling '~', '', '/', and '\\'."""
        if not path_elements:
            return Path()

        # Start with handling the first element specially if it indicates a root or home directory
        first_elem = path_elements[0]
        if first_elem in ['~', '', '/', '\\']:
            if first_elem == '~':
                # Path relative to user's home directory
                base_path = Path.home()
            elif first_elem in ['', '/', '\\']:
                # Absolute path starting from root
                base_path = Path('/')
            return base_path.joinpath(*path_elements[1:])
        elif ':' in first_elem and len(first_elem) == 2 and first_elem[1] == ':':
            # Windows-specific: path starts with a drive letter
            return Path(first_elem).joinpath(*path_elements[1:])
        else:
            # Normal path construction
            return Path(*path_elements)

    @staticmethod
    def deconstruct_path(path):
        """Deconstruct a Path object into a list of its components, considering special cases."""
        components = []

        # Handle absolute paths, including Windows-specific drive letters
        if path.is_absolute():
            if path.drive:
                components.append(path.drive)
            else:
                components.append('')
            components.extend(path.parts[1:])
        elif path.home() in path.parents:
            # Handle paths relative to the home directory
            components.append('~')
            components.extend(path.relative_to(Path.home()).parts)
        else:
            # Handle relative paths
            components.extend(path.parts)

        return components


# Example Usage:
if __name__ == "__main__":
    # Test cases for constructing paths
    print("Testing Path Construction:")
    test_elements = [
        (['~', 'projects', 'example'], "Home directory relative"),
        (['/', 'usr', 'bin'], "Root directory"),
        (['', 'usr', 'bin'], "Absolute path from root"),
        (['C:', 'Users', 'example'], "Windows drive letter"),
        (['..', 'another_folder'], "Relative path"),
        (['usr', 'bin'], "Additional relative path"),
        (['~', '.rexdblinker', 'connectionconfigs'], "RexPath")
    ]
    for elements, description in test_elements:
        path = PathUtils.construct_path(elements)
        print(f"{description} Path: {path}")

    # Test cases for deconstructing paths
    print("\nTesting Path Deconstruction:")
    test_paths = [
        (Path.home().joinpath('projects', 'example'), "Home directory relative"),
        (Path('/usr/bin'), "Root directory"),
        (Path('usr/bin'), "Relative path from current directory"),  # Corrected description
        (Path('C:/Users/example'), "Windows drive letter"),
        (Path('../another_folder'), "Relative path")
    ]
    for path, description in test_paths:
        path_list = PathUtils.deconstruct_path(path)
        print(f"{description} Path List: {path_list}")



