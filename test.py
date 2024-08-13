#!/usr/bin/env python3

import pytest
from dashboard import transform_link_path


@pytest.mark.parametrize(("filepath", "expected"),
                         [
    ("/", ""),
    ("//", ""),
    ("./", ""),
    (".//", ""),
    ("/test", "test"),
    ("./test", "test"),
    ("/test.json", "test-json"),
    ("./test.json", "test-json"),
    ("test", "test"),
    ("test.json", "test-json"),
]
)
def test_transform_link_path(filepath, expected):
    assert transform_link_path(filepath) == expected
