import frappe
from frappe.tests import IntegrationTestCase

from easynav.api.navigation import build_navigation, get_navigation, get_user_navigation
from easynav.easynav.doctype.easynav_user_navigation.test_easynav_user_navigation import (
	make_navigation,
	make_user,
)

DOCTYPE = "EasyNav User Navigation"
IGNORE_TEST_RECORD_DEPENDENCIES = ["User"]


class TestNavigationAPI(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.settings = frappe.get_doc("EasyNav Settings")
		self.settings.enabled = 1
		self.settings.position = "Top Left"
		self.navigation = make_navigation("Administrator")

	def _add(self, **kw):
		self.navigation.append("items", {"label": "X", "type": "DocType", "link_to": "User", **kw})

	def _save(self):
		self.settings.save()
		self.navigation.save()
		return build_navigation()

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_disabled_and_empty(self):
		self.settings.enabled = 0
		self.assertFalse(self._save()["enabled"])
		self.settings.enabled = 1
		data = self._save()
		self.assertTrue(data["enabled"])
		self.assertEqual(data["items"], [])
		self.assertEqual(data["position"], "top-left")

	def test_order_and_disabled_filtering(self):
		self._add(label="C", order=0)
		self._add(label="B", order=2)
		self._add(label="A", order=1)
		self._add(label="Off", order=3, enabled=0)
		self.assertEqual([i["label"] for i in self._save()["items"]], ["A", "B", "C"])

	def test_routes(self):
		self._add(label="List", link_to="User")
		self._add(label="Single", link_to="System Settings")
		self._add(label="Site", type="URL", link_to=None, url="https://example.com", open_in_new_tab=1)
		items = {i["label"]: i for i in self._save()["items"]}
		self.assertEqual(items["List"]["route"], ["List", "User"])
		self.assertEqual(items["List"]["path"], "/app/user")
		self.assertEqual(items["Single"]["route"], ["Form", "System Settings"])
		self.assertEqual(items["Site"]["url"], "https://example.com")
		self.assertTrue(items["Site"]["open_in_new_tab"])

	def test_doc_view_routes(self):
		expected = {
			"": (["List", "User"], "/app/user"),
			"List": (["List", "User", "List"], "/app/user/view/list"),
			"Report Builder": (["List", "User", "Report"], "/app/user/view/report"),
			"Dashboard": (["List", "User", "Dashboard"], "/app/user/view/dashboard"),
			"New": (["user", "new"], "/app/user/new"),
			"Calendar": (["List", "User", "Calendar", "default"], "/app/user/view/calendar/default"),
			"Kanban": (["List", "User", "Kanban"], "/app/user/view/kanban"),
			"Image": (["List", "User", "Image"], "/app/user/view/image"),
		}
		for doc_view in expected:
			self._add(label=doc_view or "Default", doc_view=doc_view)
		self._add(label="Single", link_to="System Settings", doc_view="List")
		items = {i["label"]: i for i in self._save()["items"]}
		for doc_view, (route, path) in expected.items():
			item = items[doc_view or "Default"]
			self.assertEqual((item["route"], item["path"]), (route, path), doc_view)
		self.assertEqual(items["Single"]["route"], ["Form", "System Settings"])

	def test_dashboard_route(self):
		if not frappe.db.exists("Dashboard", "EasyNav Test Dashboard"):
			frappe.get_doc({"doctype": "Dashboard", "dashboard_name": "EasyNav Test Dashboard"}).insert(
				ignore_permissions=True
			)
		self._add(label="Dash", type="Dashboard", link_to="EasyNav Test Dashboard")
		item = self._save()["items"][0]
		self.assertEqual(item["route"], ["dashboard-view", "EasyNav Test Dashboard"])
		self.assertEqual(item["path"], "/app/dashboard-view/EasyNav Test Dashboard")

	def test_invalid_item_is_skipped(self):
		self._add(label="Good")
		self._save()
		# bypass save-time validation to simulate bad stored data
		frappe.db.set_value("EasyNav Item", self.navigation.items[0].name, "url", "javascript:alert(1)")
		frappe.db.set_value("EasyNav Item", self.navigation.items[0].name, "type", "URL")
		frappe.clear_cache()
		self.assertEqual(build_navigation()["items"], [])

	def test_permission_filtering_and_guest(self):
		self._add(label="Sys", link_to="System Settings")
		self._add(label="Users", link_to="User")
		self._save()
		self.assertEqual(len(build_navigation()["items"]), 2)
		frappe.set_user("Guest")
		self.assertFalse(build_navigation()["enabled"])
		self.assertEqual(build_navigation()["items"], [])
		frappe.set_user("Administrator")

		email = make_user("easynav-test@example.com", [])
		make_navigation(
			email,
			[
				{"label": "Sys", "type": "DocType", "link_to": "System Settings"},
				{"label": "Users", "type": "DocType", "link_to": "User"},
			],
		)
		frappe.set_user(email)
		labels = [i["label"] for i in get_navigation()["items"]]
		self.assertNotIn("Sys", labels)
		self.assertIn("Users", labels)

	def test_items_are_per_user(self):
		user_a = make_user("easynav-a@example.com", ["Script Manager"])
		user_b = make_user("easynav-b@example.com", ["Script Manager"])
		make_navigation(user_a, [{"label": "A1", "type": "URL", "url": "https://example.com/a"}])
		make_navigation(user_b, [{"label": "B1", "type": "URL", "url": "https://example.com/b"}])
		self._add(label="Admin")
		self._save()

		for user, labels in ((user_a, ["A1"]), (user_b, ["B1"]), ("Administrator", ["Admin"])):
			frappe.set_user(user)
			self.assertEqual([i["label"] for i in get_navigation()["items"]], labels, user)

	def test_user_without_navigation_gets_empty_menu(self):
		user = make_user("easynav-a@example.com", ["Script Manager"])
		frappe.set_user("Administrator")
		frappe.delete_doc(DOCTYPE, user, ignore_permissions=True, ignore_missing=True)
		self._save()

		frappe.set_user(user)
		data = build_navigation()
		self.assertTrue(data["enabled"])
		self.assertEqual(data["items"], [])
		# reading the menu never creates the document
		self.assertFalse(frappe.db.exists(DOCTYPE, user))

	def test_get_user_navigation_creates_once(self):
		user = make_user("easynav-a@example.com", ["Script Manager"])
		frappe.delete_doc(DOCTYPE, user, ignore_permissions=True, ignore_missing=True)

		frappe.set_user(user)
		self.assertEqual(get_user_navigation(), user)
		doc = frappe.get_doc(DOCTYPE, user)
		self.assertEqual(doc.user, user)
		doc.check_permission("write")

		doc.append("items", {"label": "Mine", "type": "URL", "url": "https://example.com"})
		doc.save()
		self.assertEqual(get_user_navigation(), user)
		self.assertEqual(len(frappe.get_doc(DOCTYPE, user).items), 1)

	def test_get_user_navigation_rejects_guest(self):
		self.assertNotIn(get_user_navigation, frappe.guest_methods)
		frappe.set_user("Guest")
		self.assertRaises(frappe.PermissionError, get_user_navigation)
		self.assertFalse(frappe.db.exists(DOCTYPE, "Guest"))
