import sys
import os.path
import re


class LibEntry:
    name = ""
    imports = []
    functions = {}

    def __init__(self, name, imports, functions):
        self.name = name
        self.imports = imports
        self.functions = functions


class FunctionEntry:
    name = ""
    text = ""
    visited = False
    required = False

    def __init__(self, name, text, visited):
        self.name = name
        self.text = text
        self.visited = visited


def process(file_path):
    lib_base_path = get_lib_basepath(file_path)
    libraries = dict()
    # scan main file
    text = read_file(file_path)
    imports = get_imports(text)
    dependencies = scan_text(imports, text)
    # remove imports and directives from the main file text
    text = remove_imports_directives(text)
    # walk dependency tree
    while len(dependencies) > 0:
        new_dependencies = []
        for lib_name in dependencies:
            if lib_name not in libraries:
                libraries[lib_name] = parse_library(os.path.join(lib_base_path, lib_name) + ".ks")
            lib = libraries[lib_name]
            for func_name in dependencies[lib_name]:
                func = lib.functions[func_name]
                if not func.visited:
                    func.visited = True
                    function_deps = scan_text(lib.imports, func.text)
                    new_dependencies.append(function_deps)
        dependencies = merge_dicts(new_dependencies)
    # merge the script and the libraries
    return merge_new_file(text, libraries)


def get_lib_basepath(file_path):
    last_path = ""
    current_path = file_path
    while current_path != last_path:
        # walk the path towards the parent until one folder contains the "lib" folder
        last_path = current_path
        current_path = os.path.dirname(current_path)
        lib_path = os.path.join(current_path, "lib")
        if os.path.exists(lib_path):
            return lib_path


def remove_imports_directives(text):
    # regex patterns
    patterns = [
        [r"^@LAZYGLOBAL (on|off)\.", r""],              # remove LAZYGLOBAL
        [r"^runoncepath\(\"/lib/[a-zA-Z]+\"\).", r""]   # remove imports
    ]
    # apply the replacements
    for p in patterns:
        text = re.sub(p[0], p[1], text, flags=re.MULTILINE)
    return text


def merge_new_file(text, libraries):
    text_elements = []
    function_replacements = []
    # append library functions
    func_pattern = "local function {0} {1}"
    for lib in libraries.values():
        for func in lib.functions.values():
            if func.visited:
                old_name = lib.name + ":" + func.name
                new_name = lib.name + "_" + func.name
                function_replacements.append([old_name, new_name])
                text_elements.append(func_pattern.format(new_name, func.text))
    # append main script
    text_elements.append(text)
    # concatenate all together
    new_text = "\n".join(text_elements)
    # apply function replacements
    for repl in function_replacements:
        new_text = new_text.replace(repl[0], repl[1])
    # return merged text
    return new_text


def get_imports(text):
    return re.findall(r"^runoncepath\(\"/lib/([a-zA-Z]+)\"\).", text, flags=re.MULTILINE)


def scan_text(imports, text):
    # find calls to library functions in the text (ignoring commented lines)
    pattern = r"^(?:(?!\/\/).)*{LIBNAME}:([a-zA-Z0-9]+)[(@]"
    dependencies = dict()
    for lib_name in imports:
        functions = re.findall(pattern.replace("{LIBNAME}", lib_name), text, flags=re.MULTILINE)
        if len(functions) > 0:
            if lib_name not in dependencies:
                dependencies[lib_name] = set()
            dependencies[lib_name].update(functions)
    return dependencies


def merge_dicts(dict_list):
    merged = {}
    if len(dict_list) > 0:
        for d in dict_list:
            for k, v in d.items():
                if k in merged:
                    merged[k].update(v)
                else:
                    merged[k] = v
    return merged


def parse_library(file_path):
    text = read_file(file_path)
    # get library name
    lib_name = re.search(r"^global ([a-zA-Z]+Lib)", text, flags=re.MULTILINE).group(1)
    # find imported libraries
    imports = get_imports(text)
    # add the library's own name to the imports to handle calls to other top-level functions
    imports.append(lib_name)
    # extract top-level functions and their text
    functions = re.findall(r"\n\s{4}local function ([a-zA-Z0-9]+)\s*(.+?\n\s{4}})", text, flags=re.DOTALL)
    # create a dictionary with a FunctionEntry object for every function
    function_dict = {x[0]: FunctionEntry(x[0], x[1], False) for x in functions}
    # add this lib namespace to calls to functions in the same library
    add_lib_namespace(lib_name, function_dict)
    # create a LibEntry object
    lib_entry = LibEntry(lib_name, imports, function_dict)
    return lib_entry


def add_lib_namespace(lib_name, function_dict):
    function_names = function_dict.keys()
    pattern = r"({NAME})(?=[(@])"
    replacement = lib_name + r":\1"
    for func in function_dict.values():
        for fn in function_names:
            func.text = re.sub(pattern.replace("{NAME}", fn), replacement, func.text)


def read_file(file_path):
    # open the file
    with open(file_path, "r") as f:
        return f.read()


def main():
    if len(sys.argv) == 2:
        file_path = sys.argv[-1]
        text = process(file_path)
        # print the output to stdout so it can be piped to other utilities
        print(text)


if __name__ == "__main__":
    main()
