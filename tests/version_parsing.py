import re


# find_version = re.compile(r"(?P<version>(\d*)(\.a|b|rc?\d*)?(\.[post|dev]?\d*)?)").match
find_version = re.compile(r"^(?P<namever>(?P<name>.+?)-(?P<version>(\d*)(.(a|b|rc)?\d*)?(.(post|dev)?\d*)?))$").match
# find_version = re.compile(r"^(?P<namever>(?P<name>.+?)-(?P<version>\d.*?))$").match
print(find_version('ddvla-14.rc2.dev0').groupdict())
