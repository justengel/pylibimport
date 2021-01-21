"""
This is not supported less than Python 3.6
"""
import os
THIS_DIR = os.path.dirname(__file__)


def test_get_versions_module():
    import pylibimport
    versions = pylibimport.get_versions('numpy', min_version='1.19.0', exclude='1.19.1')
    assert len(versions) > 0


def test_install_module():
    import pylibimport
    assert pylibimport.install(THIS_DIR + '/sub/import_dir/custom.py', THIS_DIR + '/sub/target_dir')


def test_lib_import_module():
    import pylibimport

    # Install first
    pylibimport.install(THIS_DIR + '/sub/import_dir/custom.py', THIS_DIR + '/sub/target_dir')

    # Test import
    module = pylibimport.lib_import(THIS_DIR + '/sub/target_dir/custom.py')
    assert module is not None


if __name__ == '__main__':
    test_get_versions_module()
    test_install_module()
    test_lib_import_module()

    print('All tests finished successfully!')
