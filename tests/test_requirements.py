# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from unittest import TestCase
from pyup.requirements import Requirement
from unittest.mock import patch, MagicMock, NonCallableMagicMock, PropertyMock
from pyup.requirements import RequirementFile, RequirementsBundle
from pyup.pullrequest import PullRequest
from pyup.package import Package
import os
from datetime import datetime


def package_factory(name, versions):
    p = Package(name=name)
    p._versions = versions
    return p


class RequirementUpdateContent(TestCase):
    def test_update_content_simple_pinned(self):
        with patch('pyup.requirements.Requirement.latest_version', new_callable=PropertyMock, return_value="1.4.2"):
            content = "Django==1.4.1"
            req = Requirement.parse(content, 0)

            self.assertEqual(req.update_content(content), "Django==1.4.2")

        with patch('pyup.requirements.Requirement.latest_version', new_callable=PropertyMock, return_value="1.4.2"):
            content = "django==1.4.1"
            req = Requirement.parse(content, 0)

            self.assertEqual(req.update_content(content), "django==1.4.2")

    def test_update_content_simple_unpinned(self):
        with patch('pyup.requirements.Requirement.latest_version', new_callable=PropertyMock, return_value="1.4.2"):
            content = "django"
            req = Requirement.parse(content, 0)

            self.assertEqual(req.update_content(content), "django==1.4.2")

        with patch('pyup.requirements.Requirement.latest_version', new_callable=PropertyMock, return_value="1.4.2"):
            content = "Django"
            req = Requirement.parse(content, 0)

            self.assertEqual(req.update_content(content), "Django==1.4.2")

    def test_update_content_simple_unpinned_with_comment(self):
        with patch('pyup.requirements.Requirement.latest_version', new_callable=PropertyMock, return_value="1.4.2"):
            content = "django # newest django release"
            req = Requirement.parse(content, 0)

            self.assertEqual(req.update_content(content), "django==1.4.2 # newest django release")

        with patch('pyup.requirements.Requirement.latest_version', new_callable=PropertyMock, return_value="1.4.2"):
            content = "Django #django"
            req = Requirement.parse(content, 0)

            self.assertEqual(req.update_content(content), "Django==1.4.2 #django")

        with patch('pyup.requirements.Requirement.latest_version', new_callable=PropertyMock, return_value="1.4.2"):
            content = "Django #django #yay this has really cool comments ######"
            req = Requirement.parse(content, 0)

            self.assertEqual(req.update_content(content),
                             "Django==1.4.2 #django #yay this has really cool comments ######")

    def test_update_content_with_package_in_comments(self):
        with patch('pyup.requirements.Requirement.latest_version', new_callable=PropertyMock, return_value="2.58.1.44"):
            content = 'raven==5.8.1\n' \
                      '{%- endif %}\n\n' \
                      '{% if cookiecutter.use_newrelic == "y" -%}\n' \
                      '# Newrelic agent for performance monitoring\n' \
                      '# -----------------------------------------\n' \
                      'newrelic\n' \
                      '{%- endif %}\n\n'
            req = Requirement.parse("newrelic", 0)
            updated_content = 'raven==5.8.1\n' \
                              '{%- endif %}\n\n' \
                              '{% if cookiecutter.use_newrelic == "y" -%}\n' \
                              '# Newrelic agent for performance monitoring\n' \
                              '# -----------------------------------------\n' \
                              'newrelic==2.58.1.44\n' \
                              '{%- endif %}\n\n'
            self.assertEqual(req.update_content(content), updated_content)


class RequirementTestCase(TestCase):
    def test_is_pinned(self):
        req = Requirement.parse("Django", 0)
        self.assertEqual(req.is_pinned, False)

        req = Requirement.parse("Django==1.4,>1.5", 0)
        self.assertEqual(req.is_pinned, False)

        req = Requirement.parse("Django===1.4", 0)
        self.assertEqual(req.is_pinned, False)

        req = Requirement.parse("Django<=1.4,>=1.33", 0)
        self.assertEqual(req.is_pinned, False)

        req = Requirement.parse("Django==1.4", 0)
        self.assertEqual(req.is_pinned, True)

    def test_is_loose(self):
        req = Requirement.parse("Django", 0)
        self.assertEqual(req.is_loose, True)

        req = Requirement.parse("Django==1.4,>1.5", 0)
        self.assertEqual(req.is_loose, False)

        req = Requirement.parse("Django===1.4", 0)
        self.assertEqual(req.is_loose, False)

        req = Requirement.parse("Django<=1.4,>=1.33", 0)
        self.assertEqual(req.is_loose, False)

        req = Requirement.parse("Django==1.4", 0)
        self.assertEqual(req.is_loose, False)

    def test_filter(self):
        req = Requirement.parse("Django", 0)
        self.assertEqual(req.filter, False)

        req = Requirement.parse("Django #rq.filter:", 0)
        self.assertEqual(req.filter, False)

        req = Requirement.parse("Django #rq.filter: >=1.4,<1.5", 0)
        self.assertEqual(req.filter, [('>=', '1.4'), ('<', '1.5')])

        req = Requirement.parse("Django #rq.filter:!=1.2", 0)
        self.assertEqual(req.filter, [('!=', '1.2')])

        req = Requirement.parse("Django #rq.filter:foo", 0)
        self.assertEqual(req.filter, False)

        req = Requirement.parse("bliss #rq.filter:", 0)
        self.assertEqual(req.filter, False)

    def test_get_latest_version_within_specs(self):
        latest = Requirement.get_latest_version_within_specs(
            (("==", "1.2"), ("!=", "1.2")),
            ["1.2", "1.3", "1.4", "1.5"]
        )

        self.assertEqual(latest, None)

        latest = Requirement.get_latest_version_within_specs(
            (("==", "1.2.1"),),
            ["1.2.0", "1.2.1", "1.2.2", "1.3"]
        )

        self.assertEqual(latest, "1.2.1")

    def test_latest_version_within_specs(self):
        with patch('pyup.requirements.Requirement.package', new_callable=PropertyMock,
                   return_value=package_factory("bliss", versions=["1.9rc1", "1.9", "1.8.1", "1.8", "1.7", "1.6"])):
            req = Requirement.parse("bliss #rq.filter:", 0)
            self.assertEqual(req.latest_version_within_specs, "1.9")

            req = Requirement.parse("bliss==1.8rc1 #rq.filter:", 0)
            self.assertEqual(req.prereleases, True)
            self.assertEqual(req.latest_version_within_specs, "1.9rc1")

            req = Requirement.parse("bliss #rq.filter: >=1.7,<1.9", 0)
            self.assertEqual(req.latest_version_within_specs, "1.8.1")


        with patch('pyup.requirements.Requirement.package', new_callable=PropertyMock,
                   return_value=package_factory("gevent",
                              versions=['1.1rc1', '1.1b6', '1.1b5', '1.1b4', '1.1b3', '1.1b2', '1.1b1', '1.1a2',
                                        '1.1a1', '1.0.2', '1.0.1', ])):
            req = Requirement.parse("gevent==1.1b6", 0)
            self.assertEqual(req.latest_version_within_specs, "1.1rc1")
            self.assertEqual(req.latest_version, "1.1rc1")

    def test_version_unpinned(self):
        with patch('pyup.requirements.Requirement.package', new_callable=PropertyMock,
                   return_value=package_factory(name="django", versions=["1.9", "1.8"])):
            r = Requirement.parse("Django", 0)
            self.assertEqual(r.version, "1.9")

        with patch('pyup.requirements.Requirement.package', new_callable=PropertyMock,
                   return_value=package_factory(name="django", versions=["1.9rc1", "1.9", "1.8"])):
            r = Requirement.parse("Django", 0)
            self.assertEqual(r.version, "1.9")

        with patch('pyup.requirements.Requirement.package', new_callable=PropertyMock,
                   return_value=package_factory(name="django", versions=["1.9.1", "1.8", "1.9rc1"])):
            r = Requirement.parse("django", 0)
            self.assertEqual(r.version, "1.9.1")

        with patch('pyup.requirements.Requirement.package', new_callable=PropertyMock,
                   return_value=package_factory(name="django", versions=["1.4.3", "1.5", "1.4.2", "1.4.1", ])):
            r = Requirement.parse("Django  # rq.filter: >=1.4,<1.5", 0)
            self.assertEqual(r.version, "1.4.3")

        with patch('pyup.requirements.Requirement.package', new_callable=PropertyMock,
                   return_value=package_factory(name="django", versions=["1.8.1", "1.8"])):
            r = Requirement.parse("Django  # rq.filter: != 1.8.1", 0)
            self.assertEqual(r.version, "1.8")

        with patch('pyup.requirements.Requirement.package', new_callable=PropertyMock,
                   return_value=package_factory(name="django", versions=["1.9rc1", "1.9.1", "1.8", ])):
            r = Requirement.parse("django  # rq.filter: bogus", 0)
            self.assertEqual(r.version, "1.9.1")

    def test_version_pinned(self):
        with patch('pyup.requirements.Requirement.package', new_callable=PropertyMock,
                   return_value=package_factory(name="django", versions=["1.8", "1.9"])):
            r = Requirement.parse("Django==1.9", 0)
            self.assertEqual(r.version, "1.9")

        with patch('pyup.requirements.Requirement.package', new_callable=PropertyMock,
                   return_value=package_factory(name="django==1.9rc1", versions=["1.8", "1.9rc1", "1.9rc2"])):
            r = Requirement.parse("Django==1.9.2.rc14 # rq.filter != 1.44", 0)
            self.assertEqual(r.version, "1.9.2.rc14")

    def test_prereleases(self):
        r = Requirement.parse("Django==1.9rc1", 0)
        self.assertEqual(r.prereleases, True)

        r = Requirement.parse("Django==1.9-b1", 0)
        self.assertEqual(r.prereleases, True)

        r = Requirement.parse("Django==1.9-alpha1", 0)
        self.assertEqual(r.prereleases, True)

        r = Requirement.parse("Django", 0)
        self.assertEqual(r.prereleases, False)

        r = Requirement.parse("Django>=1.5,<=1.6", 0)
        self.assertEqual(r.prereleases, False)

        r = Requirement.parse("Django!=1.9", 0)
        self.assertEqual(r.prereleases, False)

    def test_name(self):
        r = Requirement.parse("Django==1.9rc1", 0)
        self.assertEqual(r.name, "Django")

        r = Requirement.parse("django==1.9-b1", 0)
        self.assertEqual(r.name, "django")


class RequirementsFileTestCase(TestCase):
    def test_parse_empty_line(self):
        content = """
        """
        r = RequirementFile("r.txt", content=content)
        self.assertEqual(r.requirements, [])
        self.assertEqual(r._other_files, [])

    def test_parse_comment_line(self):
        content = """
# the comment is here
        """
        r = RequirementFile("r.txt", content=content)
        self.assertEqual(r.requirements, [])
        self.assertEqual(r._other_files, [])

    def test_unsupported_line_start(self):
        content = """
-f foo
--find-links bla
-i bla
--index-url bla
--extra-index-url bla
--no-index bla
--allow-external
--allow-unverified
-Z
--always-unzip
        """
        r = RequirementFile("r.txt", content=content)
        self.assertEqual(r.requirements, [])
        self.assertEqual(r._other_files, [])

    @patch("pyup.requirements.Requirement.package")
    def test_parse_requirement(self, package):
        package.return_value = True
        content = """
-e common/lib/calc
South==1.0.1
pycrypto>=2.6
git+https://github.com/pmitros/pyfs.git@96e1922348bfe6d99201b9512a9ed946c87b7e0b
distribute>=0.6.28, <0.7
# bogus comment
-e .
pdfminer==20140328
-r production/requirements.txt
--requirement test.txt
        """
        r = RequirementFile("r.txt", content=content)

        self.assertEqual(
            r.other_files, [
                "production/requirements.txt",
                "test.txt"
            ]
        )

        self.assertEqual(
            r.requirements, [
                Requirement.parse("South==1.0.1", 3),
                Requirement.parse("pycrypto>=2.6", 4),
                Requirement.parse("distribute>=0.6.28, <0.7", 6),
                Requirement.parse("pdfminer==20140328", 3),
            ]
        )

    def test_resolve_file(self):
        resolved = RequirementFile.resolve_file("base/requirements.txt", "-r requirements/production.txt")
        self.assertEqual(resolved, "base/requirements/production.txt")

        resolved = RequirementFile.resolve_file("base/requirements.txt", "-r requirements/production.txt # prod file")
        self.assertEqual(resolved, "base/requirements/production.txt")

        resolved = RequirementFile.resolve_file("requirements.txt", "-r production.txt # prod file")
        self.assertEqual(resolved, "production.txt")


class RequirementsBundleTestCase(TestCase):
    def test_has_file(self):
        reqs = RequirementsBundle()
        self.assertEqual(reqs.has_file("foo.txt"), False)
        self.assertEqual(reqs.has_file(""), False)
        reqs.add(RequirementFile(path="foo.txt", content=''))
        self.assertEqual(reqs.has_file("foo.txt"), True)

    def test_add(self):
        reqs = RequirementsBundle()
        self.assertEqual(reqs.requirement_files, [])
        reqs.add(RequirementFile(path="foo.txt", content=''))
        self.assertEqual(reqs.requirement_files[0].path, "foo.txt")