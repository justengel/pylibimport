# from PyInstaller import config
# from PyInstaller.utils.hooks import collect_data_files
#
# # pip requirements if using python code (pip_proc or get_pip_main())
# datas = collect_data_files('pip')
# hiddenimports = [
#     'setuptools',
#     'distutils',
#     'pkg_resources',
#     ]
#
# try:
#     import pip._internal.commands
#     hiddenimports.extend([v.module_path for v in pip._internal.commands.commands_dict.values()])
# except (ImportError, AttributeError, Exception):
#     hiddenimports.extend([
#         'pip._internal.commands.install',
#         'pip._internal.commands.download',
#         'pip._internal.commands.uninstall',
#         'pip._internal.commands.freeze',
#         'pip._internal.commands.list',
#         'pip._internal.commands.show',
#         'pip._internal.commands.check',
#         'pip._internal.commands.config',
#         'pip._internal.commands.search',
#         'pip._internal.commands.cache',
#         'pip._internal.commands.wheel',
#         'pip._internal.commands.hash',
#         'pip._internal.commands.completion',
#         'pip._internal.commands.debug',
#         'pip._internal.commands.help',
#         ])


try:
    from pylibimport import find_file

    # Include the pip.exe file in your application
    binaries = [(find_file('pip.exe', 'pip3', 'pip'), '.')]

except (ImportError, Exception):
    pass
