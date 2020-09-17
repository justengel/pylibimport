

def run_simple():
    import pylibimport

    importer = pylibimport.VersionImporter(install_dir='./sub/target_dir')

    custom = importer.import_module('./sub/custom.py')
    print(custom.run_custom())
    # 'hello custom1'

    # Remove the saved module from the install_dir
    importer.delete_installed(custom)

    # Give a version number to the module
    custom = importer.import_module('./sub/custom.py', '1.0.0')
    print(custom.run_custom())
    # 'hello custom1'

    # pylibimport always adds an import_name to sys.modules (custom 1.0.0 becomes custom_1_0_0)
    import custom_1_0_0
    print(custom_1_0_0.run_custom())


if __name__ == '__main__':
    run_simple()
