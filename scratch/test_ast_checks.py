import os
import sys

# Violate Rule 1: Missing encoding in open
def read_data():
    with open("data.txt", "r") as f:
        return f.read()

# Violate Rule 2: Hardcoded Path separators in split
def parse_path(p):
    parts = p.split("/")
    return parts

# Violate Rule 3: Hardcoded path separators in concat
def join_path_concat(dir_path, name):
    return dir_path + "/" + name

# Violate Rule 4: Hardcoded path separators in f-strings
def join_path_fstring(dir_path, name):
    return f"{dir_path}/{name}"

# Violate Rule 5: Silent error handling
def unsafe_execution():
    try:
        x = 1 / 0
    except Exception:
        pass

# Violate Rule 6: Function stub
def empty_placeholder():
    """
    This is an empty function stub.
    """
    pass
