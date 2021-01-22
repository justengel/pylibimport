import pylibimport
import multiprocessing as mp


if __name__ == '__main__':
    importer = pylibimport.VersionImporter(install_dir='./sub/target_dir')

    importer.pip = pylibimport.pip_main
    # importer.pip = pylibimport.pip_bin

    # mp.freeze_support()
    # importer.pip = pylibimport.pip_proc_flag
    # importer.pip = pylibimport.pip_proc  # pip_proc uses light_process.LightProcess which allows this outside of main

    mod = importer.install('./sub/import_dir/dynamicmethod-1.0.4-py3-none-any.whl', 'dynamicmethod', '1.0.4')

    pylibimport.run_pip('--help')
    print(mod)
