import os
import urllib
import json
import shutil
from pathlib import Path
from bs4 import BeautifulSoup
import unittest
from django.test import TransactionTestCase, TestCase  # noqa
from django.urls import reverse
from django.db.models import Q
from textwrap import dedent as twdd
# noinspection PyUnresolvedReferences
from ipydex import IPS  # noqa
from django.conf import settings

# assume directory structure as in README
if not os.environ.get("PYERK_BASE_DIR"):
    os.environ["PYERK_BASE_DIR"] = \
        Path("./").joinpath("..", "erk-data-for-unittests", "erk-ocse").absolute().as_posix()

os.environ["PYERK_BASE_DIR"] = os.path.abspath(os.environ["PYERK_BASE_DIR"])


# if this fails the tests should not be run
assert os.path.isdir(os.environ["PYERK_BASE_DIR"]), f'path not found: {os.environ["PYERK_BASE_DIR"]}'

# noinspection PyUnresolvedReferences
import pyerkdjango.util  # noqa
import pyerk  as p

# this is relevant for switching off some database optimizations which are incompatible with django.test.TestCase
# because every testcase rewinds its transactions
settings.RUNNING_TESTS = True

# now when pyerk has been imported, we can initialize the respective settings
settings.LC.initialize_pyerk_settings()


# noinspection PyUnresolvedReferences
from pyerkdjango import models  # noqa

# The tests can be run with
# `python manage.py test`
# `python manage.py test --rednose` # with colors


# noinspection PyUnresolvedReferences
from pyerkdjango.util import w, u, q_reverse, urlquote  # noqa


os.environ["UNITTEST"] = "True"

MATH_URI = "erk:/ocse/0.2/math"
CT_URI = "erk:/ocse/0.2/control_theory"

# for now this is the same as in the pyerk-tests
__URI__ = TEST_BASE_URI = "erk:/local/unittest"


# this serves to print the test-method-name before it is executed (useful for debugging, see setUP below)
PRINT_TEST_METHODNAMES = True


class HouskeeperMixin:
    """
    Class to provide common functions for all our TestCase subclasses
    """

    def setUp(self):
        self.print_methodnames()
        self.register_this_module()
        if method := getattr(self, "custom_setUp", None):
            assert callable(method)
            method()


    def tearDown(self) -> None:
        self.unload_all_mods()
        if method := getattr(self, "custom_tearDown", None):
            assert callable(method)
            method()

    def print_methodnames(self):
        cls = self.__class__
        method_repr = f"{cls.__module__}:{cls.__qualname__}.{self._testMethodName}"
        os.environ["UNITTEST_METHOD_NAME"] = method_repr
        if PRINT_TEST_METHODNAMES:
            # noinspection PyUnresolvedReferences
            print("In method", pyerkdjango.util.aux.bgreen(method_repr))

    @staticmethod
    def unload_all_mods():
        p.unload_mod(TEST_BASE_URI, strict=False)

        # unload all modules which where loaded by a test
        for mod_id in list(p.ds.mod_path_mapping.a.keys()):
            p.unload_mod(mod_id)

    @staticmethod
    def register_this_module():
        keymanager = p.KeyManager()
        p.register_mod(TEST_BASE_URI, keymanager, prefix="ut")


class Test_01_Basics(HouskeeperMixin, TestCase):
    """
    Ensure that the testmodule itself works as expected
    """

    def test01_home_page(self):
        url = reverse("landingpage")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

    def test02_home_page(self):
        # load the landing page again to see if tests interact (not wantend)
        url = reverse("landingpage")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

    def test03_home_page_modules_loading_behavior(self):
        # load the landing page again to see if tests interact (not wantend)
        url = reverse("landingpage")

        # initial state: ocse test data should not be loaded
        res = self.client.get(url)
        content = res.content.decode("utf8")
        self.assertEqual(res.status_code, 200)

        self.assertNotIn(f"utc_loaded_module:{MATH_URI}", content)
        self.assertNotIn(f"utc_loaded_module:{CT_URI}", content)

        # ensure only test module is loaded
        self.assertIn(TEST_BASE_URI, p.ds.mod_path_mapping.a)
        self.assertEqual(len(p.ds.mod_path_mapping.a), 1)
        # now load the data
        pyerkdjango.util.reload_data_if_necessary(speedup=False)
        self.assertNotEqual(len(p.ds.mod_path_mapping.a), 0)

        res = self.client.get(url)
        content = res.content.decode("utf8")
        self.assertIn(f"utc_loaded_module:{MATH_URI}", content)
        self.assertIn(f"utc_loaded_module:{CT_URI}", content)


class Test_02_MainApp(HouskeeperMixin, TestCase):
    def custom_setUp(self):
        # set `speedup` to False because TestCase disallows things like `transaction.set_autocommit(False)`

        # force is necessary: the database is emptied after each test, but the DB_ALREADY_LOADED flag remains true
        pyerkdjango.util.reload_data_if_necessary(speedup=False, force=True)

    def test01_home_page1(self):

        # get url by its unique name, see urls.py

        url = reverse("landingpage")
        res = self.client.get(url)

        # `utc` means "unit test comment"
        # this is a simple mechanism to ensure the desired content actually was delivered
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "utc_landing_page")

    def test02_search_api(self):
        url = "/search/?q=set"
        res = self.client.get(url)

        soup = BeautifulSoup(res.content.decode("utf8"), "lxml")

        script_tags = soup.findAll("script")

        for tag in script_tags:
            # this assumes that Item I13 has not changed its label since the test was written
            if tag.contents and (tag.contents[0] == '\\"I13[\\\\\\"mathematical set\\\\\\"]\\"'):
                break
        else:
            self.assertTrue(False, "could not find expected copy-string in response")

    def test03_entity_detail_view(self):
        url = reverse("entitypage", kwargs=dict(uri=w("I12")))
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        content = res.content.decode("utf8")
        self.assertIn(
            '<span class="entity-key highlight"><a href="/e/erk%253A%252Fbuiltins%2523I12">I12</a></span>', content
        )

        src1 = twdd(
            """
            <span class="entity-key highlight"><a href="/e/erk%253A%252Fbuiltins%2523I12">I12</a></span><!--
            --><!--
            --><!--
            -->["<span class="entity-label" title="base class for any knowledge object of interrest in the field of mathematics">mathematical object</span>"]<!--
            -->
            <div class="entity-description">base class for any knowledge object of interrest in the field of mathematics</div>
            """
        )
        self.assertIn(src1, content)

        url = "/search/?q=bound"
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

    def test04_entity_detail_view2(self):
        # test displaying an entity from a loaded module

        # note: currently the ocse is already loaded in the views
        # mod1 = p.erkloader.load_mod_from_path(TEST_DATA_PATH2, prefix="ct")
        url = reverse("entitypage", kwargs=dict(uri=w("ct__I9907")))
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        # TODO: add some actual test code here (which was probaly forgotten earlier)
        # likely it was intended to test context-rendering

    def test05_sparql_page(self):
        url = reverse("sparqlpage")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

        url = (
            "/sparql/?query=%0D%0APREFIX+%3A+%3Cerk%3A%2F%3E%0D%0ASELECT+*%0D%0AWHERE"
            "+%7B%0D%0A++++%3Fs+%3AR5+%3Fo.%0D%0A%7D%0D%0A"
        )
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

    def test06_reload_via_url(self):
        url = reverse("reload")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 302)

    def test07_LanguageSpecifiedString(self):

        with p.uri_context(uri=TEST_BASE_URI):

            I900 = p.create_item(
                R1__has_label="default label",
                R1__has_label__de="deutsches label" @ p.de,
            )

        pyerkdjango.util.reload_data_if_necessary(force=True, speedup=False)

        _ = models.LanguageSpecifiedString.objects.create(langtag="en", content="test1")
        t2 = models.LanguageSpecifiedString.objects.create(langtag="de", content="test1")
        res = models.LanguageSpecifiedString.objects.filter(langtag="de")
        self.assertGreaterEqual(len(res), 1)

        self.assertIn(t2, res)
        x = models.Entity.objects.get(uri=u("ut__I900"))
        res = x.label.filter(langtag="en")
        self.assertGreaterEqual(len(res), 1)

        _ = x.label.all()

        q = "sta"
        res = models.Entity.objects.filter(
            Q(label__content__icontains=q) | Q(uri__icontains=q) | Q(description__icontains=q)
        )
        self.assertGreater(len(res), 5)

    def test08_web_visualization1(self):
        # mod1 = p.erkloader.load_mod_from_path(TEST_DATA_PATH2, prefix="ct")
        self.assertIn("ct", p.ds.uri_prefix_mapping.b)

        url = reverse("entityvisualization", kwargs=dict(uri=w("ct__I9907")))
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

        test_str = f"utc_visualization_of_{u('ct__I9907')}"
        content = res.content.decode("utf8")

        with open("tmp.txt", "w") as txtfile:
            txtfile.write(content)
        self.assertIn(test_str, content)

        # test if labels have visualization links:

        # note: when hovering over the links firefox displays the unquoted version of this url
        # i.e.: /e/erk:%2Focse%2F0.2#I9906/v

        item_url = "/e/erk%253A%252Focse%252F0.2%252Fmath%2523I9906/v"

        txt = f'<a href="{item_url}">I9906'

        self.assertIn(txt, content)

        url_vis = reverse("entityvisualization", kwargs={"uri": urlquote(u("ma__I9906"))})
        assert url_vis.endswith("/v")

        # the following is necessary due to the temporary replace-hack views.entity_view, see bookmark://vis01

        # noinspection PyUnresolvedReferences
        url_vis2 = urllib.parse.unquote(url_vis)
        url_vis3 = urllib.parse.unquote(url_vis2)
        url_vis_empirical2 = urllib.parse.unquote(item_url)
        url_vis_empirical3 = urllib.parse.unquote(url_vis_empirical2)
        self.assertEqual(url_vis_empirical3, url_vis3)

        # test label formating

        soup = BeautifulSoup(content, "lxml")
        svg_tag = soup.findAll("svg")[0]

        # TODO: make this independet of changing data
        link1, link2 = svg_tag.findAll(name="a", attrs={"href": item_url})

        self.assertEqual(link1.parent.parent.name, "g")
        self.assertEqual(link1.parent.parent.get("class"), ["node"])
        self.assertEqual(link1.text, "I9906")
        self.assertEqual(link2.text, '["square matrix"]')

    def test09_get_auto_complete_list_api(self):

        url = reverse("get_auto_complete_list")
        res = self.client.get(url)

        completion_suggestions = json.loads(res.content)["data"]

        self.assertGreater(len(completion_suggestions), 50)

    def test10_editor_view(self):

        url = reverse("show_editor")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        content = res.content.decode("utf8")
        self.assertNotIn("utc_error", content)
        self.assertIn("utc_editor_page", content)

        uri = MATH_URI
        url = reverse("show_editor_with_uri", kwargs=dict(uri=uri))
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        content = res.content.decode("utf8")
        self.assertNotIn("utc_error", content)
        self.assertIn(f"utc_uri_of_loaded_file:{uri}", content)

        uri = "wrong:/bad-uri"
        url = reverse("show_editor_with_uri", kwargs=dict(uri=uri))
        res = self.client.get(url)
        content = res.content.decode("utf8")
        self.assertIn("utc_error_page", content)

    def test11_api_save_file(self):

        url = reverse("save_file")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)


class Test_03_Utils(HouskeeperMixin, unittest.TestCase):

    fpath = "_test.txt"
    backup_dir = "_backup"

    def custom_tearDown(self):

        try:
            shutil.rmtree(self.backup_dir)
        except OSError:
            pass

        try:
            os.remove(self.fpath)
        except OSError:
            pass

    def test_savetxt(self):
        test_content = "#abcedfg123"

        self.assertFalse(os.path.exists(self.fpath))

        pyerkdjango.util.savetxt(self.fpath, test_content, backup=False)
        self.assertTrue(os.path.exists(self.fpath))

        # test backup
        self.assertFalse(os.path.exists(self.backup_dir))
        pyerkdjango.util.savetxt(self.fpath, test_content, backup=True)
        self.assertTrue(os.path.exists(self.backup_dir))

        dir_content = os.listdir(self.backup_dir)
        self.assertEqual(len(dir_content), 1)
