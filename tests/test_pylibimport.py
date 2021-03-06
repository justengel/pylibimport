import os
import sys


def make_importer():
    from pylibimport.lib_import import VersionImporter
    v = VersionImporter(download_dir='./sub/import_dir/',  # Where to find available imports
                        install_dir='./sub/target_dir',  # Where to save imports/installs to
                        install_dependencies=False,  # .whl files install dependencies in install_dir?
                        reset_modules=True)              # Reset sys.modules after import removing dependencies?
    v.cleanup()  # Delete the install_dir (Needed for testing)
    v.init()
    v.error = lambda *args: None
    return v


def test_available_modules():
    v = make_importer()

    assert len(tuple(v.iter_downloaded_versions())) > 0
    assert len(next(v.iter_downloaded_versions())) > 0
    assert len(tuple(v.iter_installed_versions())) == 0
    assert isinstance(v.available_modules()[0], tuple)


def test_find_module():
    v = make_importer()

    # Find by path
    name, version, import_name, path = v.find_module('dynamicmethod-1.0.2.zip')
    assert name is not None and version is not None and import_name is not None and path is not None

    # Find by path
    name, version, import_name, path = v.find_module('dynamicmethod-1.0.2.tar.gz')
    assert name is not None and version is not None and import_name is not None and path is not None

    # Find by name and version
    name, version, import_name, path = v.find_module('dynamicmethod', '1.0.2')
    assert name is not None and version is not None and import_name is not None and path is not None

    # Find latest by name
    name, version, import_name, path = v.find_module('dynamicmethod')
    assert version is not None and version != '1.0.2', 'Did not find the latest module by name correctly.'


def test_import_path():
    v = make_importer()
    v.download_dir = '.'

    # Use path not connected to download_dir
    custom = v.import_path(os.path.abspath('./sub/import_dir/custom.py'))
    assert custom is not None
    assert custom.run_custom() == 'hello'


def test_import_module():
    v = make_importer()

    custom = v.import_module('custom.py')
    assert custom is not None
    assert custom.run_custom() == 'hello'

    # Import same name, but give a version number
    custom1 = v.import_module(os.path.abspath('./sub/custom.py'), '0.0.1')
    assert custom1 is not None
    assert custom != custom1
    assert custom1.run_custom() != 'hello'

    # Regular import new version. pylibimport always adds name_version to sys.modules.
    import custom_0_0_1
    assert custom_0_0_1 is custom1
    assert custom_0_0_1.run_custom() != 'hello'


def test_delete_installed():
    import shutil
    v = make_importer()

    module_path = v.make_import_path('dynamicmethod', '1.0.2')
    if os.path.exists(module_path):
        shutil.rmtree(module_path)

    # Delete as module
    module = v.import_module('dynamicmethod-1.0.2.zip')
    assert module is not None
    assert os.path.exists(module_path)
    v.delete_installed(module)
    assert not os.path.exists(module_path)

    # Delete as name
    m1 = v.import_module('dynamicmethod-1.0.2.zip')
    module = v.import_module('dynamicmethod')  # Will be latest version in download_dir
    assert module is not None
    assert os.path.exists(v.make_import_path('dynamicmethod', '1.0.4'))
    v.delete_installed('dynamicmethod')  # Will delete the latest version.
    assert not os.path.exists(v.make_import_path('dynamicmethod', '1.0.4'))

    # Delete as name version
    module = v.import_module('dynamicmethod', '1.0.2')  # Will be latest version in download_dir
    assert module is not None
    assert os.path.exists(module_path)
    v.delete_installed('dynamicmethod', '1.0.2')  # Will delete the latest version.
    assert not os.path.exists(module_path)

    # THIS IS NOT AVAILABLE ANYMORE!
    # # Delete as import name
    # module = v.import_module('dynamicmethod_1_0_2')
    # assert module is not None
    # assert os.path.exists(module_path)
    # v.delete_installed('dynamicmethod_1_0_2')
    # assert not os.path.exists(module_path)


def test_import_zip():
    v = make_importer()

    dynamicmethod = v.import_module('dynamicmethod-1.0.2.zip')
    assert dynamicmethod is not None
    assert dynamicmethod.dynamicmethod is not None

    dynamicmethod = v.import_module('dynamicmethod-1.0.2.tar.gz')
    assert dynamicmethod is not None
    assert dynamicmethod.dynamicmethod is not None

    # Make sure repeat is the same.
    dynamicmethod2 = v.import_module('dynamicmethod-1.0.2.tar.gz')
    assert dynamicmethod2 is not None
    assert dynamicmethod is dynamicmethod2


def test_multi_import_zip():
    v = make_importer()

    dynamicmethod_1_0_2 = v.import_module('dynamicmethod-1.0.2.tar.gz')
    assert dynamicmethod_1_0_2 is not None
    assert dynamicmethod_1_0_2.dynamicmethod is not None

    dynamicmethod_1_0_3 = v.import_module('dynamicmethod-1.0.3.tar.gz')
    assert dynamicmethod_1_0_3 is not None
    assert dynamicmethod_1_0_3.dynamicmethod is not None

    assert dynamicmethod_1_0_3.dynamicmethod != dynamicmethod_1_0_2.dynamicmethod


def test_whl_install():
    v = make_importer()

    module = v.import_module('dynamicmethod-1.0.3-py3-none-any.whl')
    assert module is not None
    assert hasattr(module, 'dynamicmethod')
    # assert module.__version__ == '1.0.3'  # Does not have attr
    assert module.__import_version__ == '1.0.3'  # Custom variable from pylibimport

    module = v.import_module('dynamicmethod-1.0.4-py3-none-any.whl')
    assert module is not None
    assert module.__version__ == '1.0.4'


def test_download():
    v = make_importer()
    v.download('continuous_threading', '1.2.1')
    _, _, _, filename = v.find_module('continuous_threading', '1.2.1')
    assert os.path.exists(filename)
    v.delete_downloaded('continuous_threading', '1.2.1')  # or v.delete('continuous_threading', '1.2.1')
    assert not os.path.exists(filename)


def test_contained_modules():
    from pylibimport.install import import_module

    # Save modules that this import uses
    dependent_modules = {}
    custom = import_module('./sub/import_dir/custom.py', reset_modules=True, clean_modules=True,
                           dependent_modules=dependent_modules)
    assert custom is not None
    assert 'functools' in dependent_modules
    assert list(sys.modules.keys()) != list(dependent_modules.keys())


if __name__ == '__main__':
    test_available_modules()
    test_find_module()
    test_import_path()
    test_import_module()
    test_delete_installed()

    test_import_zip()
    test_multi_import_zip()
    test_whl_install()

    test_download()

    test_contained_modules()

    print('All tests finished successfully!')
