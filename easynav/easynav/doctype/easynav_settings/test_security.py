import frappe
from frappe.tests import IntegrationTestCase

from easynav.api.navigation import build_navigation, get_navigation

PASSWORD_FREE = {"send_welcome_email": 0}


def _make_user(email: str, roles: list[str]):
	if frappe.db.exists("User", email):
		user = frappe.get_doc("User", email)
	else:
		user = frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": email.split("@")[0], **PASSWORD_FREE}
		).insert(ignore_permissions=True)
	user.roles = []
	for role in roles:
		user.append("roles", {"role": role})
	user.save(ignore_permissions=True)
	return email


class TestEasyNavSecurity(IntegrationTestCase):
	"""EasyNav is a navigation utility: it must never show more than Frappe itself would allow."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.limited = _make_user("easynav-limited@example.com", [])  # User C
		cls.blogger = _make_user("easynav-blogger@example.com", ["Blogger"])  # User A
		cls.manager = _make_user("easynav-manager@example.com", ["System Manager"])  # User B

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
		settings.items = []
		for label, type_, target in (
			("Settings", "DocType", "System Settings"),
			("Blog Post", "DocType", "Blog Post"),
			("Report", "Report", "EasyNav Test Report"),
			("Site", "URL", "https://example.com"),
		):
			settings.append("items", {"label": label, "type": type_, "target": target})
		settings.save()

	def tearDown(self):
		frappe.set_user("Administrator")

	def _labels(self, user):
		return [i["label"] for i in build_navigation(user)["items"]]

	def test_restricted_user_only_sees_public_items(self):
		labels = self._labels(self.limited)
		self.assertNotIn("Settings", labels)
		self.assertNotIn("Report", labels)
		self.assertNotIn("Blog Post", labels)
		self.assertIn("Site", labels)  # URLs are not permission controlled

	def test_blogger_sees_blog_post_only(self):
		labels = self._labels(self.blogger)
		self.assertIn("Blog Post", labels)
		self.assertNotIn("Settings", labels)
		self.assertNotIn("Report", labels)

	def test_system_manager_sees_only_what_frappe_allows(self):
		# System Manager has no Blog Post permission, so EasyNav must hide it too
		self.assertEqual(self._labels(self.manager), ["Settings", "Report", "Site"])

	def test_session_user_is_restored(self):
		frappe.set_user(self.limited)
		build_navigation(self.manager)
		self.assertEqual(frappe.session.user, self.limited)

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
		self.assertTrue(build_navigation("Guest")["items"] == [])

	def test_stored_unsafe_urls_are_never_returned(self):
		settings = frappe.get_doc("EasyNav Settings")
		unsafe = ("javascript:alert(1)", "data:text/html,x", "//evil.com", "ftp://x")
		for row, url in zip(settings.items, unsafe, strict=True):
			frappe.db.set_value("EasyNav Item", row.name, {"type": "URL", "target": url})
		frappe.clear_cache()
		self.assertEqual(self._labels("Administrator"), [])
