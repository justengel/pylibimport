import prep_modules  # Uses pylibimport for custom_1_0_0

import custom_1_0_0
print(custom_1_0_0.run_custom())

import custom_0_0_0
print(custom_0_0_0.run_custom())

# This actually works! ... code completion is not going to happen. Maybe I could learn more about the import hooks.
