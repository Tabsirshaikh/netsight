import numpy as np


def test_package_imports_and_has_version():
    import netsight

    assert netsight.__version__ == "0.1.0"


def test_core_dependencies_import():
    import pyxtf  # noqa: F401
    import rasterio  # noqa: F401

    assert int(np.__version__.split(".")[0]) >= 2
