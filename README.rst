===========
pylibimport
===========
Python utility for importing packages with the same name, but different version.

VersionImporter Attributes:
  * import_dir - Directory to find import names and files
  * target_dir - Directory to save/install modules by names and version
  * install_dependencies - If True .whl files will install dependencies to the target_dir
  * reset_modules - Reset sys.modules after every import (Will still add custom_0_0_0).

   * This helps prevent dependencies from being saved to sys.modules

  * modules - dictionary of name and version modules that have been imported.


Import options:
  * Module import - import normal .py files.
  * Zip import - import .zip files or .tar.gz sdist files.
  * Wheel import - import .whl files. This really installs them to a target dir then imports it.


Example
=======

Simple import example.

.. code-block:: python

    import pylibimport

    importer = pylibimport.VersionImporter(target_dir='./sub/target_dir')

    custom = importer.import_module('./sub/custom.py')
    print(custom.run_custom())
    # 'hello custom1'

    # Remove the saved module from the target_dir
    importer.delete_module(custom)

    # Give a version number to the module
    custom = importer.import_module('./sub/custom.py', '1.0.0')
    print(custom.run_custom())
    # 'hello custom1'

    # pylibimport always adds an import_name to sys.modules (custom 1.0.0 becomes custom_1_0_0)
    import custom_1_0_0
    print(custom_1_0_0.run_custom())


Multiple Files
~~~~~~~~~~~~~~

This library also works across multiple files.

.. code-block:: python

    # prep_modules.py
    import pylibimport

    importer = pylibimport.VersionImporter(target_dir='./sub/target_dir')
    importer.import_module('./sub/custom.py', '1.0.0')  # Give a version number to the module
    importer.import_module('./sub/import_dir/custom.py', '0.0.0')


The prep_modules.py uses pylibimport to import modules with version into sys.modules
allowing imports from other files.

.. code-block:: python

    # multi_modules.py
    import prep_modules  # Uses pylibimport for custom_1_0_0 and custom_0_0_0

    import custom_1_0_0
    print(custom_1_0_0.run_custom())

    import custom_0_0_0
    print(custom_0_0_0.run_custom())

    # This actually works! ... code completion is not going to happen.
    # Python has a bunch of import hooks (ZipImporter) which could make this better?


Problems
========

Most importing works without any help. You just add the path to sys.path and import.
You can also easily import a zip file by adding the zip file to the path and importing it.
A .whl file could just be renamed .zip and import like the zip file.

The biggest problem is C extensions. C extensions require you to extract the .pyd from the .zip before importing.
Originally I was going to automate only extracting the .pyd files. It is much easier to extract the entire zip file or
install the .whl file. This also lets you extract/install once and leave it on your system, making imports easier later.

This approach also lets you separate things by version number which may be useful.

Numpy
~~~~~

Don't try this with Numpy or .whl files that want to install Numpy. Numpy is compiled against other libraries
and the pathing gets messed up. I have not had any success importing numpy without a regular install.
I tried a lot of different ways on Windows 10 with Python 3.8 - 64 Bit.
I think I even tried Numpy found at https://www.lfd.uci.edu/~gohlke/pythonlibs/.


Future
======

I would like to learn more about python's import system. I would like to research how zipimport
works with the finder and loader. Unfortunately, I know myself, and it's probably not going to happen.
In the end Python will eventually add version import support anyway. Future Python syntax will probably be
like qml :code:`import custom 1.0.0`.
