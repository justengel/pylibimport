import pylibimport

# Downloaded whl
filename = "./sub/import_dir/opencv_python-4.5.1.48-cp38-cp38-win_amd64.whl"

imp = pylibimport.VersionImporter(install_dir='./sub/target_dir')
# imp.install(filename, 'cv2', '4.5.1')  # Install with name cv2
# cv2_4_5_1 = imp.import_module('cv2', '4.5.1')

# Use import chain if import is different from name ('cv2.other' same as "import cv2.other")
cv2_4_5_1 = imp.install(filename, 'opencv', '4.5.1', import_chain='cv2')  # Optional name and version with whl file.

print(dir(cv2_4_5_1))
