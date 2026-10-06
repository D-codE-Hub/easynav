import frappe
from frappe.tests import IntegrationTestCase

from easynav.api.navigation import build_navigation, get_navigation
from easynav.easynav.doctype.easynav_user_navigation.test_easynav_user_navigation import (
	make_navigation,
	make_user,
)

IGNORE_TEST_RECORD_DEPENDENCIES = ["User"]


class TestEasyNavSecurity(IntegrationTestCase):
	"""EasyNav is a navigation utility: it must never show more than Frappe itself would allow."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.limited = make_user("easynav-limited@example.com", [])  # User C
		cls.scripter = make_user("easynav-scripter@example.com", ["Script Manager"])  # User A
		cls.manager = make_user("easynav-manager@example.com", ["System Manager"])  # User B

		if not frappe.db.exists("Report", "EasyNav Test Report"):
			frappe.get_doc(
				{
					"doctype": "Report",
					"report_name": "EasyNav Test Report",
					"ref_doctype": "ToDo",
					"report_type": "Report Builder",
					"is_standard": "No",
					"roles": [{"role": "System Manager"}],
				}
			).insert(ignore_permissions=True)

	def setUp(self):
		frappe.set_user("Administrator")
		settings = frappe.get_doc("EasyNav Settings")
		settings.enabled = 1
		settings.save()

		# every user configures the same items; each must only get back what Frappe lets them open
		items = [
			{"label": label, "type": type_, ("url" if type_ == "URL" else "link_to"): target}
			for label, type_, target in (
				("Settings", "DocType", "System Settings"),
				("Server Script", "DocType", "Server Script"),
				("Report", "Report", "EasyNav Test Report"),
				("Site", "URL", "https://example.com"),
			)
		]
		for user in ("Administrator", self.limited, self.scripter, self.manager):
			make_navigation(user, items)

	def tearDown(self):
		frappe.set_user("Administrator")

	def _labels(self, user):
		frappe.set_user(user)
		return [i["label"] for i in build_navigation()["items"]]

	def test_restricted_user_only_sees_public_items(self):
		labels = self._labels(self.limited)
		self.assertNotIn("Settings", labels)
		self.assertNotIn("Report", labels)
		self.assertNotIn("Server Script", labels)
		self.assertIn("Site", labels)  # URLs are not permission controlled

	def test_script_manager_sees_server_script_only(self):
		labels = self._labels(self.scripter)
		self.assertIn("Server Script", labels)
		self.assertNotIn("Settings", labels)
		self.assertNotIn("Report", labels)

	def test_system_manager_sees_only_what_frappe_allows(self):
		# System Manager has no Server Script permission, so EasyNav must hide it too
		self.assertEqual(self._labels(self.manager), ["Settings", "Report", "Site"])

	def test_payload_has_no_settings_internals(self):
		frappe.set_user(self.limited)
		data = get_navigation()
		self.assertEqual(set(data), {"enabled", "position", "button", "items"})
		for item in data["items"]:
			self.assertNotIn("name", item)
			self.assertNotIn("owner", item)

	def test_cannot_read_settings_directly(self):
		frappe.set_user(self.limited)
		self.assertFalse(frappe.has_permission("EasyNav Settings", "read"))
		self.assertFalse(frappe.has_permission("EasyNav Settings", "write"))

	def test_api_is_not_guest_accessible(self):
		self.assertNotIn(get_navigation, frappe.guest_methods)
		frappe.set_user("Guest")
		self.assertTrue(build_navigation()["items"] == [])

	def test_stored_unsafe_urls_are_never_returned(self):
		navigation = frappe.get_doc("EasyNav User Navigation", "Administrator")
		unsafe = ("javascript:alert(1)", "data:text/html,x", "//evil.com", "ftp://x")
		for row, url in zip(navigation.items, unsafe, strict=True):
			frappe.db.set_value("EasyNav Item", row.name, {"type": "URL", "url": url})
		frappe.clear_cache()
		self.assertEqual(self._labels("Administrator"), [])
