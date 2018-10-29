import unittest
import tsviz
import re


class Tests(unittest.TestCase):
    def test_parse_module_import_regexp(self):
        decl = "import { class } from \"./File\";"
        m = tsviz.module_import_declaration.match(decl)

        self.assertNotEqual(None, m)
        [filename] = m.groups()
        self.assertEqual("./File", filename)

        decl = "import { class, class 2 } from \"./File\";"
        m = tsviz.module_import_declaration.match(decl)

        self.assertNotEqual(None, m)
        [filename] = m.groups()
        self.assertEqual("./File", filename)

        decl = "import * as boo from \"./File\";"
        m = tsviz.module_import_declaration.match(decl)

        self.assertNotEqual(None, m)
        [filename] = m.groups()
        self.assertEqual("./File", filename)

    def test_module_id(self):
        module = tsviz.Module("SuperOffice.Test.Name.ts")
        self.assertEqual("SuperOffice_Test_Name_ts", module.get_friendly_id())

        module = tsviz.Module("SubDir/SuperOffice.Test.Name.ts")
        self.assertEqual("SubDir_SuperOffice_Test_Name_ts", module.get_friendly_id())

    def test_graphviz_output(self):
        proj1 = tsviz.Module("Module.SO.Main.ts")
        proj2 = tsviz.Module("Module.SO.Installer.ts")

        proj1.add_dependency(proj2.name);

        txt = tsviz.render_dot_file([proj1, proj2])

        # has no trace of dotted IDs
        self.assertEqual(True, "Module_SO_Main" in txt)
        self.assertEqual(True, "Module_SO_Installer" in txt)

        # has proper labels
        self.assertEqual(True, "label=\"Module.SO.Main.ts\"" in txt)

    def test_eliminate_dependencies(self):
        a = tsviz.Module("A.ts")
        b = tsviz.Module("B.ts")
        c = tsviz.Module("C.ts")
        d = tsviz.Module("D.ts")

        a.dependant_modules = [b, c, d]
        b.dependant_modules = [c, d]
        c.dependant_modules = [d]

        a.remove_transitive_dependencies()
        b.remove_transitive_dependencies()
        c.remove_transitive_dependencies()

        self.assertEqual([b], a.dependant_modules)
        self.assertEqual([c], b.dependant_modules)
        self.assertEqual([d], c.dependant_modules)

    def test_dependency_chains(self):
        a = tsviz.Module("A.ts")
        b = tsviz.Module("B.ts")
        c = tsviz.Module("C.ts")
        d = tsviz.Module("D.ts")

        a.dependant_modules = [b]
        b.dependant_modules = [c]
        c.dependant_modules = [d]

        all_deps = a.get_nested_dependencies()
        self.assertEqual([b, c, d], all_deps)

    def test_module_highlighting(self):
        a = tsviz.Module("A.ts")
        b1 = tsviz.Module("B1.ts")
        b2 = tsviz.Module("B2.ts")
        c = tsviz.Module("C.ts")

        a.dependant_modules = [b1, b2]
        b1.dependant_modules = [c]

        c.highlight = True

        self.assertEqual(True, a.has_highlighted_dependencies())
        self.assertEqual(True, b1.has_highlighted_dependencies())
        self.assertEqual(False, b2.has_highlighted_dependencies())
        self.assertEqual(False, c.has_highlighted_dependencies())

    def test_declared_dependencies_generates_highlight_even_though_dependency_is_eliminated_as_transitive(self):
        a = tsviz.Module("A.ts")
        b = tsviz.Module("B.ts")
        c = tsviz.Module("C.ts")

        a.dependant_modules = [b]
        b.dependant_modules = [c]
        # for a, c is a declared, transitive dependency which will normally be eliminated
        # in visualization.
        a.declared_dependant_modules = [b,c]
        b.declared_dependant_modules = [c]

        c.highlight = True

        hasDep = a.has_declared_highlighted_dependencies()
        self.assertEqual(True, hasDep)

    def test_missing_shared_transitive_dependencies(self):
        a = tsviz.Module("A.ts")
        b = tsviz.Module("B.ts")

        a.add_dependency(b.filename)
        a.add_dependency("C")
        b.add_dependency("C")

        modules = [a, b]
        a.resolve_modules_from_names(modules)
        b.resolve_modules_from_names(modules)

        self.assertEqual(True, a.has_missing_modules)
        self.assertEqual(True, b.has_missing_modules)

        self.assertEqual(["C.ts"], a.missing_module_names)
        self.assertEqual(["C.ts"], b.missing_module_names)

        # TODO: test with eliminated transisitive deps.

    def test_circular_dependencies_are_flagged(self):
        a = tsviz.Module("A.ts")
        b = tsviz.Module("B.ts")
        c = tsviz.Module("C.ts")
        d = tsviz.Module("D.ts")

        a.add_dependency(b.filename)
        b.add_dependency(c.filename)
        c.add_dependency(d.filename)
        # so far so good... but then suddenly...
        # circular dependency!
        c.add_dependency(b.filename)

        tsviz.process_modules([a, b, c, d])

        self.assertEqual(False, a.has_circular_dependencies)
        self.assertEqual(True, b.has_circular_dependencies)
        self.assertEqual(True, c.has_circular_dependencies)
        self.assertEqual(False, d.has_circular_dependencies)

        self.assertEqual([c], b.circular_dependencies)
        self.assertEqual([b], c.circular_dependencies)

    def test_deep_circular_dependencies_are_flagged(self):
        a = tsviz.Module("A.ts")
        b = tsviz.Module("B.ts")
        c = tsviz.Module("C.ts")
        d = tsviz.Module("D.ts")

        a.add_dependency(b.filename)
        b.add_dependency(c.filename)
        c.add_dependency(d.filename)
        # so far so good... but then suddenly...
        # deep circular dependency!
        d.add_dependency(b.filename)

        tsviz.process_modules([a, b, c, d])

        self.assertEqual(False, a.has_circular_dependencies)
        self.assertEqual(True, b.has_circular_dependencies)
        self.assertEqual(True, c.has_circular_dependencies)
        self.assertEqual(True, d.has_circular_dependencies)

        self.assertEqual([d], b.circular_dependencies)
        self.assertEqual([b], c.circular_dependencies)
        self.assertEqual([c], d.circular_dependencies)

    def test_highlighting_top_level_node_flags_dependants(self):
        a = tsviz.Module("A.ts")
        b = tsviz.Module("B.ts")
        c = tsviz.Module("C.ts")
        d = tsviz.Module("D.ts")

        a.add_dependency(b.filename)
        b.add_dependency(c.filename)
        c.add_dependency(d.filename)

        tsviz.process_modules([a, b, c, d])

        # act
        highlighter = re.compile("^a")
        tsviz.highlight_modules(highlighter, [a, b, c, d])

        # assert
        self.assertEqual(False, a.highlighted_dependents)
        self.assertEqual(True, b.highlighted_dependents)
        self.assertEqual(True, c.highlighted_dependents)
        self.assertEqual(True, d.highlighted_dependents)


if __name__ == "__main__":
    unittest.main()
