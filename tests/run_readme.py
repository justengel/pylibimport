

def run_manual():
    import pylibimport

    # Manual function
    installed = pylibimport.install_lib("./sub/import_dir/custom.py", './sub/plugins')

    # Can also call the module
    installed = pylibimport.install("./sub/import_dir/custom.py", './sub/plugins')

    custom = pylibimport.import_module("./sub/plugins/custom.py")
    assert custom.run_custom() == 'hello'


def run_simple():
    import pylibimport

    importer = pylibimport.VersionImporter(install_dir='./sub/target_dir')

    custom = importer.import_module('./sub/import_dir/custom.py')
    assert custom.run_custom() == 'hello'

    # Give a version number to the module
    custom1 = importer.import_module('./sub/custom.py', '1.0.0')
    assert custom1.run_custom() == 'hello custom1'

    # pylibimport always adds an import_name to sys.modules (custom 1.0.0 becomes custom_1_0_0)
    import custom_1_0_0
    assert custom_1_0_0 is custom1
    assert custom_1_0_0.run_custom() == 'hello custom1'

    # Remove the saved module from the install_dir
    importer.delete_installed(custom)
    importer.delete_installed(custom_1_0_0)


if __name__ == '__main__':
    run_manual()
    run_simple()
