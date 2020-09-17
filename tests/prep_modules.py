import pylibimport

importer = pylibimport.VersionImporter(install_dir='./sub/target_dir')
importer.import_module('./sub/custom.py', '1.0.0')  # Give a version number to the module
importer.import_module('./sub/import_dir/custom.py', '0.0.0')
