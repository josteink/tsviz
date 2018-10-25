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

    def test_parse_module_dependency_regexp(self):
        decl = "		{62AB4DC9-9913-4686-9F66-4BD3F4C7B119} = {62AB4DC9-9913-4686-9F66-4BD3F4C7B119}"

        m = tsviz.module_dependency_declaration.match(decl)

        self.assertNotEqual(None, m)
        [id1, id2] = m.groups()
        self.assertEqual(id1, id2)
        self.assertEqual("62AB4DC9-9913-4686-9F66-4BD3F4C7B119", id1)

    def test_parse_solution_contents(self):
        decl = """
Project("{2150E333-8FDC-42A3-9474-1A3956D46DE8}") = "DCF", "DCF", "{E6CAB0B1-AB81-40E4-9F7B-E777B2A706DE}"
EndProject
        Project("{8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942}") = "MakeDistribution", "Clients\CS\MakeDistribution\MakeDistribution.vcxproj", "{2E668CA6-63BC-4F85-8D9D-5287D80C7D6B}"
        ProjectSection(ProjectDependencies) = postProject
    {5A1B76E3-A314-4956-A50F-45475A5F330A} = {5A1B76E3-A314-4956-A50F-45475A5F330A}
        EndProjectSection
                Project("{8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942}") = "Admin", "Clients\CS\www\admin\Admin.vcxproj", "{5A1B76E3-A314-4956-A50F-45475A5F330A}"
        EndProject"""

        lines = decl.split("\n")
        projs = tsviz.analyze_modules_in_solution(lines)

        self.assertEqual(2, len(projs))

        self.assertEqual("Admin", projs[0].name)
        self.assertEqual(0, len(projs[0].dependant_ids))
        self.assertEqual("MakeDistribution", projs[1].name)
        self.assertEqual(1, len(projs[1].dependant_ids))

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
