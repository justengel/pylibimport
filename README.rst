===========
pylibimport
===========
Python utility for importing packages with the same name, but different version.

VersionImporter Attributes:
  * download_dir - Directory to find import names and files
  * install_dir - Directory to save/install modules by names and version
  * install_dependencies - If True .whl files will install dependencies to the install_dir
  * reset_modules - Reset sys.modules after every import (Will still add custom_0_0_0).

   * This helps prevent dependencies from being saved to sys.modules

  * modules - dictionary of name and version modules that have been imported.


Import options:
  * Module import - import normal .py files.
  * Zip import - import .zip files or .tar.gz sdist files.
  * Wheel import - import .whl files. This really installs them to a target dir then imports it.

    * This requires pip. See "Pip Options".


Pip Options
===========

This library now provides multiple ways of using pip. The default method is by importing pip's main function and
running it (pip_main). If you are using this in an executable `pip_bin` is recommended.


pip_main
~~~~~~~~
The pip_main option simply uses the main function found in pip. This is the default for this library.
Sometimes pip's main function will open a separate process which may cause problems with executables.

.. code-block:: python

    import pylibimport

    pylibimport.VersionImporter.pip = pylibimport.pip_main


pip_proc
~~~~~~~~
The pip_proc option uses LightProcess to create a separate process and run pip_main.

.. code-block:: python

    import pylibimport

    pylibimport.VersionImporter.pip = pylibimport.pip_proc


pip_bin
~~~~~~~
I found running the binary is the most reliable way for installing packages. This is also the best way if you are
bundling your code into an executable using PyInstaller (not as a onefile executable). The pylibimport library uses this
pip option by default. If using PyInstaller see pyinstaller_hooks/hook-pylibimport.py.

This can be changed with the following code

.. code-block:: python

    import pylibimport

    pylibimport.VersionImporter.pip = pylibimport.pip_bin


This can be extended to run the subprocess in shell mode.

.. code-block:: python

    import pylibimport

    def pip_shell(*args, **kwargs):
        return pylibimport.pip_bin(*args, shell=True, **kwargs)

    pylibimport.VersionImporter.pip = pip_shell


You should be able to use this method in a PyInstaller executable as well.
I believe in some cases pip opens a subprocess which can cause problems with multiprocessing executables.
I found pip_bin to be the most reliable method.


Example
=======

Simple import example.

.. code-block:: python

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


Multiple Files
~~~~~~~~~~~~~~

This library also works across multiple files.

.. code-block:: python

    # prep_modules.py
    import pylibimport

    importer = pylibimport.VersionImporter(install_dir='./sub/target_dir')
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


Subpackages
~~~~~~~~~~~

Now you can import sub packages as well.

.. code-block:: python

    import pylibimport

    importer = pylibimport.VersionImporter()

    module = importer.import_module('requests', '2.23.0', 'requests.auth')
    assert hasattr(module, 'HTTPBasicAuth')



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

My ultimate solution is to use pip to install the library to a location and point to that location.


Future
======

I would like to learn more about python's import system. I would like to research how zipimport
works with the finder and loader. Unfortunately, I know myself, and it's probably not going to happen.
In the end I think Python will eventually add version import support anyway or this will be done by other pipenv
library or something. Future Python (4.0) syntax will probably be like qml :code:`import custom 1.0.0` where the
version is optional. That is just my guess.

My very long term goal is to make this a virtual environment replacemnt. Right now I have 50 venv's on my computer.
I have one for every library that I develop. With this I also have a bunch of the same libraries installed.
My development environment is filled with duplicate libraries. This library can solve this problem. I do not have a
lot of time to develop this functionality, so it will take me a long time.


List and Download Versions
==========================

This library can now find versions from a simple pypi index.

.. code-block:: sh

    >>> python -m pylibimport.get_versions requests

You can also download a package in a similar way

.. code-block:: sh

    >>> python -m pylibimport.download requests -v 2.23.0
    requests-2.23.0-py2.py3-none-any.whl saved!
