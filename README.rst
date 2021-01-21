===========
pylibimport
===========
Python utility for importing packages with the same name, but different versions.

One of the major hurldes was importing .whl and .tar.gz (sdist) files. The best way to do this is to install the
library. This library has a couple of utilities to help install libraries.

The main library manager is the VersionImporter. This utility was created to point to a download directory and an
installation. Once a library is installed to the installation directory it can be imported. The importer has to modify
`sys.modules` in order to allow multiple versions.

Manual Functions:
  * import_module - import the module from a path.
  * install_lib - install a path to a destination (.py, .zip, .tar.gz, .whl)
  * register_install_type - Register a string extension or callable function with an custom installation function.


VersionImporter Attributes:
  * download_dir - Directory to find import names and files
  * install_dir - Directory to save/install modules by names and version
  * install_dependencies - If True .whl files will install dependencies to the install_dir
  * reset_modules - Reset sys.modules after every import (Will still add custom_0_0_0).

   * This helps prevent dependencies from being saved to sys.modules

  * modules - dictionary of name and version modules that have been imported.


Callable Modules:

  * pylibimport.download
  * pylibimport.get_versions
  * pylibimport.install
  * pylibimport.lib_import


Import options:
  * Module import - import normal .py files.
  * Zip import - import .zip files or .tar.gz sdist files.
  * Wheel import - import .whl files. This really installs them to a target dir then imports it.

    * This requires pip. See "Pip Options".


Example
=======

Manually call the install and import functions.

.. code-block:: python

    import pylibimport

    # Manual function
    installed = pylibimport.install_lib("./sub/import_dir/custom.py", './sub/plugins')

    # Can also call the module
    installed = pylibimport.install("./sub/import_dir/custom.py", './sub/plugins')

    custom = pylibimport.import_module("./sub/plugins/custom.py")
    assert custom.run_custom() == 'hello'


VersionImporter manager class

.. code-block:: python

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


Command Line Interface (CLI)
============================

Several modules are available to run from the command line.

.. code-block:: sh

    python -m pylibimport.get_versions --help
    python -m pylibimport.download --help
    python -m pylibimport.install --help


Problems
========

Most importing works without any help. You just add the path to sys.path and import.
You can also easily import a zip file by adding the zip file to the path and importing it.
A .whl file could just be renamed .zip and import like the zip file.

The biggest problem is C extensions. C extensions require you to extract the .pyd from the .zip before importing.
Originally I was going to automate only extracting the .pyd files. However, it is much easier to extract the
entire zip file or install the .whl file. This also lets you extract/install once and leave it on your system,
making imports easier later.

This approach also lets you separate things by version number which may be useful.

The main problem I faced was working with pip to install .whl files. These problems are explained in further in the
Pip Options section.

Pip Options
===========

Pip is pain. "pip" was written for command line use only. While there are tools to get pip to run in you applications,
they are not friendly. I am mostly using this library for plugins that are versioned. The plugins interface with a Qt
application. Running pip in a python development environment works fine. Running pip in a pyinstaller executable is a
nightmare.

I tried 3 ways of running pip.

  * pip_bin - Run pip's binary (.exe Windows)
  * pip_main - Run pip's main function
  * pip_proc - Run pip's main function in a separate process (using multiprocessing).

"pip" is primarily run as a binary (.exe Windows). The binary is compiled against your python distribution and
points to your python distribution. You cannot just copy the pip.exe and use it somewhere else. Well, you can as long
as python.exe is in the same spot. The only thing I needed pip for was downloading a .whl file and installing it into
a directory. This could work with executables, but the client application would have to have python.exe installed in
the exact same directory location as my python.exe.

The developers for pip advise against calling pip's main function. However, it is available so I am going to try it.
Overall, it worked. For my application I needed to run pip's main function using multiprocessing. This worked, but
hanged and would not finish on occasion (see pip_proc_flag).

The other major thing I tried to do was installing source files with pip (directory with setup.py).
Of course I was using C extensions to speed up my application. Turns out when pip is compiling and installing
C Extensions it calls subprocess. Subprocess does not work in a pyinstaller executable. I tried hacking this to
replace all of pip's subprocess calls to multiprocessing and well it sort of worked. In the end I abandoned
installing from source. Just compile the .whl file yourself and have your application install the .whl file.


pip_main
~~~~~~~~
The pip_main option simply uses the main function found in pip. This is the default for this library.
Sometimes pip's main function will open a separate process which may cause problems with executables. I believe pip
opens a separate process when it is trying to install a directory with a setup.py file instead of a whl file.

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
I originally found running the binary is the most reliable way for installing packages. Unfortunately, when making an
executable this appears to work on your machine because the pip.exe path matches. On other machines this probably will
not work.

.. code-block:: python

    import pylibimport

    pylibimport.VersionImporter.pip = pylibimport.pip_bin


This can be extended to run the subprocess in shell mode.

.. code-block:: python

    import pylibimport

    def pip_shell(*args, **kwargs):
        return pylibimport.pip_bin(*args, shell=True, **kwargs)

    pylibimport.VersionImporter.pip = pip_shell




Numpy
~~~~~

Numpy is now supported if installed!

Old stuff below?

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

My very long term goal is to make this a virtual environment replacement. Right now I have 50+ venv's on my computer.
I have one for every library that I develop. With this I also have a bunch of the same libraries installed.
My development environment is filled with duplicate libraries. This library can solve this problem. I do not have a
lot of time to develop this functionality, so it will take me a long time.


List and Download Versions
==========================

This library can find versions from a simple pypi index.

.. code-block:: sh

    >>> python -m pylibimport.get_versions requests

You can also download a package in a similar way

.. code-block:: sh

    >>> python -m pylibimport.download requests -v 2.23.0
    requests-2.23.0-py2.py3-none-any.whl saved!
