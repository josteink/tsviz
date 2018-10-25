#!/usr/bin/python3

#
# tsviz
#
# a command-line utility to help visualize TypeScript class-dependencies and
# graphs.
#

from argparse import ArgumentParser
import re
import os

debug_output = False
solution_path = "."

module_import_declaration = re.compile("import from \"({(.*)})\";")


def debug(txt):
    global debug_output
    if debug_output:
        print(txt)


def get_unix_path(file):
    return file.replace("\\", "/")


def get_directory(file):
    unix_file = get_unix_path(file)
    return os.path.split(unix_file)[0]


def set_working_basedir(root_dir):
    global solution_path
    solution_path = get_directory(get_unix_path(root_dir))
    debug("Base-solution dir set to {0}".format(solution_path))


class Module(object):
    def __init__(self, filename):
        self.name = self.get_name_from_filename(filename)
        self.filename = filename
        self.id = self.get_full_module_path()
        self.dependant_ids = []
        self.dependant_modules = []
        self.declared_dependant_modules = []
        self.has_missing_modules = False
        self.is_missing_module = False
        self.highlight = False

    def get_name_from_filename(self, filename):
        if len(solution_path) == 0:
            return filename
        elif solution_path == ".":
            return filename
        else:
            return filename[len(solution_path)::]

    def filter_id(self, id):
        return id.replace("-", "")

    def get_friendly_id(self):
        return self.name.replace(".ts", "").replace(".", "_").replace("-", "_").replace("/", "_")

    def add_dependency(self, id):
        id = str.upper(id)
        if id not in self.dependant_ids:
            self.dependant_ids.append(id)

    def get_full_module_path(self):
        return self.filename

    def get_module_references(self, lines):
        imports = []
        for line in lines:
            if line.startswith("import "):
                imports.append(line)
        return imports

    def get_module_ids(self, imports):
        result = []
        for item in imports:
            match = module_import_declaration.match(item)
            if match:
                result.append(match.groups()[0].upper())
        return result

    def get_declared_module_dependency_ids(self):
        full_path = self.get_full_module_path()
        if not os.path.isfile(full_path):
            print("--Module {0}-- Couldn't open file '{1}'".format(self.name, full_path))
            return []

        lines = get_lines_from_file(full_path)
        imports = self.get_module_references(lines)
        ids = self.get_module_ids(imports)
        return ids

    def apply_declared_module_dependencies(self):
        ids = self.get_declared_module_dependency_ids()
        for id in ids:
            self.add_dependency(id)

    def resolve_modules_from_ids(self, projects):
        for id in self.dependant_ids:
            project = get_module_by_id(id, projects)
            if project is None:
                # track missing deps consistently
                missing_module_id = "Missing_" + id.replace("-", "")
                project = Module(missing_module_id, missing_module_id, id)
                project.is_missing_module = True
                projects.append(project)

            if project.is_missing_module:
                self.has_missing_modules = True
                self.missing_module_ids.append(id)

            self.dependant_modules.append(project)

        self.declared_dependant_modules = self.dependant_modules

    def remove_transitive_dependencies(self):
        # if A depends on B & C, and
        # B also depends on C, then
        # A has a transitive dependency on C through B.

        # This is a dependency which can be eliminated to clean up the graph.

        # clone list to have separate object to work on
        project_deps = self.dependant_modules[:]

        # investigate each direct sub-dependency as its own tree
        for dep in self.dependant_modules:

            # calculate all dependencies for this one tree
            nested_deps = dep.get_nested_dependencies()

            # check if any of those are direct dependencues
            for nested_dep in nested_deps:
                # if so, remove them
                if nested_dep in project_deps:
                    debug("--Project {0}-- Removed transitive dependency: {1} (via {2})".format(self.name, nested_dep.name, dep.name))
                    project_deps.remove(nested_dep)

        eliminated_deps = len(self.dependant_modules) - len(project_deps)
        if eliminated_deps != 0:
            debug("--Project {0}-- Eliminated {1} transitive dependencies. Was {2}. Reduced to {3}".format(self.name, eliminated_deps, len(self.dependant_modules), len(project_deps)))

        self.dependant_modules = project_deps

    def get_nested_dependencies(self):
        # clone to new list, don't modify the existing list!
        # that means -adding- dependencies when we want to remove them!
        total_deps = self.dependant_modules[:]

        for dep in self.dependant_modules:
            dep_deps = dep.get_nested_dependencies()
            for dep_dep in dep_deps:
                if dep_dep not in total_deps:
                    total_deps.append(dep_dep)

        return total_deps

    def has_highlighted_dependencies(self):
        allDeps = self.get_nested_dependencies()
        for dep in allDeps:
            if dep.highlight:
                return True
        return False

    def has_declared_highlighted_dependencies(self):
        declaredDeps = self.declared_dependant_modules
        for dep in declaredDeps:
            if dep.highlight:
                return True
        return False



def get_module_by_id(id, projects):
    for project in projects:
        if project.id == id:
            return project
    return None


def get_lines_from_file(file):
    with open(file, 'r') as f:
        contents = f.read()
        lines = contents.split("\n")
        return lines


def sort_modules(modules):
    modules.sort(key=lambda x: x.name)


def get_tsfiles_in_dir(root_dir):
    from fnmatch import fnmatch

    results = []

    for path, subdirs, files in os.walk(root_dir):
        for name in files:
            if fnmatch(name, "*.ts"):
                results.append(os.path.join(path, name))
    return results

def analyze_modules(tsfiles):

    modules = []
    current_module = None

    for tsfile in tsfiles:
        current_module = Module(tsfile)
        modules.append(current_module)

    # pull in dependencies declared in project-files
    for module in modules:
        module.apply_declared_module_dependencies()

    # all projects & dependencies should now be known. lets analyze them
    for module in modules:
        module.resolve_modules_from_ids(modules)

    # format results in a alphabetical order
    sort_modules(modules)
    for module in modules:
        sort_modules(module.dependant_modules)

    return modules


def remove_transitive_dependencies(projects):
    for project in projects:
        project.remove_transitive_dependencies()


def filter_modules(rx, projects):
    result = []

    for project in projects:
        if not rx.match(str.lower(project.name)):
            result.append(project)
        else:
            debug("Info: Excluding project {0}.".format(project.name))

    return result


def highlight_modules(rx, projects):
    for project in projects:
        if rx.match(str.lower(project.name)):
            debug("Highlighting project {0}".format(project.name))
            project.highlight = True


def render_dot_file(projects, highlight_all=False):
    lines = []

    lines.append("digraph {")
    lines.append("    rankdir=\"TB\"")
    lines.append("")
    lines.append("    # apply theme")
    lines.append("    bgcolor=\"#222222\"")
    lines.append("")
    lines.append("    // defaults for edges and nodes can be specified")
    lines.append("    node [ color=\"#ffffff\" fontcolor=\"#ffffff\" ]")
    lines.append("    edge [ color=\"#ffffff\" ]")
    lines.append("")
    lines.append("    # project declarations")

    # define projects
    # create nodes like this
    #  A [ label="First Node" shape="circle" ]
    for project in projects:
        id = project.get_friendly_id()

        styling = ""
        if project.highlight:
            styling = " fillcolor=\"#30c2c2\" style=filled color=\"#000000\" fontcolor=\"#000000\""
        elif project.is_missing_module:
            styling = " fillcolor=\"#f22430\" style=filled color=\"#000000\" fontcolor=\"#000000\""
        elif project.has_missing_modules:
            styling = " fillcolor=\"#c2c230\" style=filled color=\"#000000\" fontcolor=\"#000000\""

        lines.append("    {0} [ label=\"{1}\" {2} ]".format(id, project.name, styling))

    # apply dependencies
    lines.append("")
    lines.append("    # project dependencies")
    for project in projects:
        proj1_id = project.get_friendly_id()
        for proj2 in project.dependant_modules:
            if proj2 is None:
                print("WARNING: Unable to resolve dependency with ID {0} for project {1}".format(id, project.name))
            else:
              proj2_id = proj2.get_friendly_id()
              styling = ""
              if proj2.highlight or proj2.has_declared_highlighted_dependencies() or (highlight_all and proj2.has_highlighted_dependencies()):
                  styling = " [color=\"#30c2c2\"]"
              elif proj2.is_missing_module or (project.has_missing_modules and proj2.has_missing_modules):
                  styling = " [color=\"#f22430\"]"
              lines.append("    {0} -> {1}{2}".format(proj1_id, proj2_id, styling))

    lines.append("")
    lines.append("}")

    return "\n".join(lines)


def process(root_dir, dot_file, exclude, highlight, highlight_all, keep_deps):
    set_working_basedir(root_dir)
    module_files = get_tsfiles_in_dir(root_dir)
    modules = analyze_modules(module_files)

    if not keep_deps:
        debug("Removing redundant dependencies...")
        remove_transitive_dependencies(modules)

    if exclude:
        debug("Excluding projects...")
        excluder = re.compile(str.lower(exclude))
        modules = filter_modules(excluder, modules)

    if highlight:
        debug("Highlighting projects...")
        highlighter = re.compile(str.lower(highlight))
        highlight_modules(highlighter, modules)

    txt = render_dot_file(modules, highlight_all)

    with open(dot_file, 'w') as f:
        f.write(txt)

    print("Wrote output-file '{0}'.".format(dot_file))


def main():
    global debug_output

    p = ArgumentParser()
    p.add_argument("--input", "-i", help="The root directory to analyze.")
    p.add_argument("--output", "-o", help="The file to write to.")
    p.add_argument("--keep-declared-deps", "-k", action="store_true", help="Don't remove redundant, transisitive dependencies in post-processing.")
    p.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    p.add_argument("--exclude", "-e", help="Filter modules matching this expression from the graph")
    p.add_argument("--highlight", help="Highlights modules matching this expression in the graph")
    p.add_argument("--highlight-all", action="store_true", help="Highlight all paths leading to a highlighted project")

    args = p.parse_args()

    debug_output = args.verbose

    process(args.input, args.output, args.exclude, args.highlight, args.highlight_all, args.keep_declared_deps)


# don't run from unit-tests
if __name__ == "__main__":
    main()
