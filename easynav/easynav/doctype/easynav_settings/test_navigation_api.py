import frappe
from frappe.tests import IntegrationTestCase

from easynav.api.navigation import build_navigation, get_navigation


class TestNavigationAPI(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.settings = frappe.get_doc("EasyNav Settings")
		self.settings.enabled = 1
		self.settings.position = "Top Left"
		self.settings.items = []

	def _add(self, **kw):
		self.settings.append("items", {"label": "X", "type": "DocType", "target": "User", **kw})

	def _save(self):
		self.settings.save()
		return build_navigation("Administrator")

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
		self._add(label="List", target="User")
		self._add(label="Single", target="System Settings")
		self._add(label="Site", type="URL", target="https://example.com", open_in_new_tab=1)
		items = {i["label"]: i for i in self._save()["items"]}
		self.assertEqual(items["List"]["route"], ["List", "User"])
		self.assertEqual(items["List"]["path"], "/app/user")
		self.assertEqual(items["Single"]["route"], ["Form", "System Settings"])
		self.assertEqual(items["Site"]["url"], "https://example.com")
		self.assertTrue(items["Site"]["open_in_new_tab"])

	def test_invalid_item_is_skipped(self):
		self._add(label="Good")
		self.settings.save()
		# bypass save-time validation to simulate bad stored data
		frappe.db.set_value("EasyNav Item", self.settings.items[0].name, "target", "javascript:alert(1)")
		frappe.db.set_value("EasyNav Item", self.settings.items[0].name, "type", "URL")
		frappe.clear_cache()
		self.assertEqual(build_navigation("Administrator")["items"], [])

	def test_permission_filtering_and_guest(self):
		self._add(label="Sys", target="System Settings")
		self._add(label="Users", target="User")
		self.settings.save()
		frappe.clear_cache()
		self.assertEqual(len(build_navigation("Administrator")["items"]), 2)
		self.assertFalse(build_navigation("Guest")["enabled"])
		self.assertEqual(build_navigation("Guest")["items"], [])

		email = "easynav-test@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "Nav", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.set_user(email)
		labels = [i["label"] for i in get_navigation()["items"]]
		self.assertNotIn("Sys", labels)
		self.assertIn("Users", labels)
