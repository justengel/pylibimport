import pylibimport
pylibimport.init_finder(download_dir='./sub/import_dir/', install_dir='./sub/target_dir')


import custom_0_0_0
print(custom_0_0_0.run_custom())


import dynamicmethod_1_0_2
import dynamicmethod_1_0_3

print(dynamicmethod_1_0_2)
print(dynamicmethod_1_0_3)
assert dynamicmethod_1_0_2 is not dynamicmethod_1_0_3
