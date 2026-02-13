import pytest
from pathlib import Path
from pgmonkey.common.utils.pathutils import PathUtils


class TestConstructPathHome:

    def test_home_directory(self):
        result = PathUtils.construct_path(['~', 'projects', 'example'])
        assert result == Path.home() / 'projects' / 'example'


class TestConstructPathRoot:

    def test_root_slash(self):
        result = PathUtils.construct_path(['/', 'usr', 'bin'])
        assert result == Path('/usr/bin')

    def test_root_empty_string(self):
        result = PathUtils.construct_path(['', 'usr', 'bin'])
        assert result == Path('/usr/bin')


class TestConstructPathRelative:

    def test_relative_path(self):
        result = PathUtils.construct_path(['usr', 'bin'])
        assert result == Path('usr/bin')

    def test_relative_parent(self):
        result = PathUtils.construct_path(['..', 'folder'])
        assert result == Path('../folder')


class TestConstructPathEmpty:

    def test_empty_list(self):
        result = PathUtils.construct_path([])
        assert result == Path()


class TestDeconstructPathAbsolute:

    def test_absolute_unix_path(self):
        components = PathUtils.deconstruct_path(Path('/usr/bin'))
        assert components[0] == ''
        assert 'usr' in components
        assert 'bin' in components


class TestDeconstructPathRelative:

    def test_relative_path(self):
        components = PathUtils.deconstruct_path(Path('usr/bin'))
        assert components == ['usr', 'bin']
