import unittest
import tsviz


class Tests(unittest.TestCase):
    def test_parse_module_import_regexp(self):
        decl = "import { class } from \"./File\""
        m = tsviz.module_declaration.match(decl)

        self.assertNotEqual(None, m)
        [filename] = m.groups()
        self.assertEqual("File", filename)

        decl = "import { class, class 2 } from \"./File\""
        m = tsviz.module_declaration.match(decl)

        self.assertNotEqual(None, m)
        [filename] = m.groups()
        self.assertEqual("File", filename)

        decl = "import * as boo from \"./File\""
        m = tsviz.module_declaration.match(decl)

        self.assertNotEqual(None, m)
        [filename] = m.groups()
        self.assertEqual("File", filename)

    def test_module_id(self):
        proj = tsviz.Module("SuperOffice.Test.Name", "stn.csproj", "123-234-345")

        self.assertEqual("SuperOffice_Test_Name", proj.get_friendly_id())

    def test_graphviz_output(self):
        proj1 = tsviz.Module("Project.SO.Main", "psomain.csproj", "123-234")
        proj2 = tsviz.Module("Project.SO.Installer", "psoinstaller.vcxproj", "234-345")

        proj1.add_dependency(proj2.id);

        txt = tsviz.render_dot_file([proj1, proj2])

        # has no trace of dotted IDs
        self.assertEqual(True, "Module_SO_Main" in txt)
        self.assertEqual(True, "Module_SO_Installer" in txt)

        # has proper labels
        self.assertEqual(True, "label=\"Project.SO.Main\"" in txt)

    def test_eliminate_dependencies(self):
        a = tsviz.Module("A", "A.csproj", "A")
        b = tsviz.Module("B", "B.csproj", "B")
        c = tsviz.Module("C", "C.csproj", "C")
        d = tsviz.Module("D", "D.csproj", "D")

        a.dependant_projects = [b, c, d]
        b.dependant_projects = [c, d]
        c.dependant_projects = [d]

        a.remove_transitive_dependencies()
        b.remove_transitive_dependencies()
        c.remove_transitive_dependencies()

        self.assertEqual([b], a.dependant_projects)
        self.assertEqual([c], b.dependant_projects)
        self.assertEqual([d], c.dependant_projects)

    def test_dependency_chains(self):
        a = tsviz.Module("A", "A.csproj", "A")
        b = tsviz.Module("B", "B.csproj", "B")
        c = tsviz.Module("C", "C.csproj", "C")
        d = tsviz.Module("D", "D.csproj", "D")

        a.dependant_projects = [b]
        b.dependant_projects = [c]
        c.dependant_projects = [d]

        all_deps = a.get_nested_dependencies()
        self.assertEqual([b, c, d], all_deps)

    def test_module_highlighting(self):
        a = tsviz.Module("A", "A.csproj", "A")
        b1 = tsviz.Module("B1", "B1.csproj", "B1")
        b2 = tsviz.Module("B2", "B2.csproj", "B2")
        c = tsviz.Module("C", "C.csproj", "C")

        a.dependant_projects = [b1, b2]
        b1.dependant_projects = [c]

        c.highlight = True

        self.assertEqual(True, a.has_highlighted_dependencies())
        self.assertEqual(True, b1.has_highlighted_dependencies())
        self.assertEqual(False, b2.has_highlighted_dependencies())
        self.assertEqual(False, c.has_highlighted_dependencies())

    def test_declared_dependencies_generates_highlight_even_though_dependency_is_eliminated_as_transitive(self):
        a = tsviz.Module("A", "A.csproj", "A")
        b = tsviz.Module("B", "B.csproj", "B")
        c = tsviz.Module("C", "C.csproj", "C")

        a.dependant_projects = [b]
        b.dependant_projects = [c]
        # for a, c is a declared, transitive dependency which will normally be eliminated
        # in visualization.
        a.declared_dependant_projects = [b,c]
        b.declared_dependant_projects = [c]

        c.highlight = True

        hasDep = a.has_declared_highlighted_dependencies()
        self.assertEqual(True, hasDep)
        
    def test_missing_shared_transitive_dependencies(self):
        a = tsviz.Module("A", "A.csproj", "A")
        b = tsviz.Module("B", "B.csproj", "B")

        a.add_dependency("B")
        a.add_dependency("C")
        b.add_dependency("C")

        projects = [a, b]
        a.resolve_projects_from_ids(projects)
        b.resolve_projects_from_ids(projects)

        self.assertEqual(True, a.has_missing_projects)
        self.assertEqual(True, b.has_missing_projects)

        self.assertEqual(["C"], a.missing_module_ids)
        self.assertEqual(["C"], b.missing_module_ids)

        # TODO: test with eliminated transisitive deps.


if __name__ == "__main__":
    unittest.main()
