
# from PyInstaller import config
# from PyInstaller.utils.hooks import collect_data_files
#
# # pip requirements if using python code (pip_proc or get_pip_main())
# datas = collect_data_files('pip')
# hiddenimports = [
#     'setuptools',
#     'distutils',
#     'pkg_resources',
#     'pip._internal.commands.install'
#     ]


try:
    from pylibimport import find_file

    # Include the pip.exe file in your application
    binaries = [(find_file('pip.exe', 'pip3', 'pip'), '.')]

except (ImportError, Exception):
    pass
