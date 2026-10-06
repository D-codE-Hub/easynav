import frappe
from frappe.tests import IntegrationTestCase

from easynav.easynav.doctype.easynav_user_navigation.test_easynav_user_navigation import make_navigation
from easynav.easynav.validation import is_safe_url

IGNORE_TEST_RECORD_DEPENDENCIES = ["User"]


class TestItemValidation(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.navigation = make_navigation("Administrator")

	def _items(self, *rows):
		"""Start again from the stored document, so a failed save cannot affect the next one."""
		self.navigation.reload()
		self.navigation.items = []
		for row in rows:
			self.navigation.append("items", {"label": "Item", "type": "DocType", "link_to": "User", **row})

	def _assert_invalid(self, *rows):
		self._items(*rows)
		with self.assertRaises(frappe.ValidationError) as raised:
			self.navigation.save()
		self.assertNotIsInstance(raised.exception, frappe.TimestampMismatchError)

	def _assert_valid(self, *rows):
		self._items(*rows)
		self.navigation.save()

	def test_valid_items(self):
		self._assert_valid(
			{}, {"label": "Site", "type": "URL", "link_to": None, "url": "https://example.com"}
		)

	def test_missing_target_and_label(self):
		self._assert_invalid({"link_to": ""})
		self._assert_invalid({"label": " "})

	def test_missing_records(self):
		for type_ in ("DocType", "Page", "Report", "Dashboard"):
			self._assert_invalid({"type": type_, "link_to": "Does Not Exist 123"})

	def test_url_items_use_url_field(self):
		# the address must come from `url`; a URL item without one is invalid
		self._assert_invalid({"label": "Site", "type": "URL", "link_to": None})
		self._assert_invalid({"label": "Site", "type": "URL", "link_to": None, "url": "javascript:alert(1)"})

	def test_doc_view_validation(self):
		self._assert_invalid({"doc_view": "Tree"})  # User is not a tree DocType
		self._assert_valid(
			{"doc_view": "Report Builder"},
			{"link_to": "System Settings", "doc_view": "Tree"},  # ignored for Single DocTypes
		)

	def test_child_table_rejected(self):
		self._assert_invalid({"link_to": "EasyNav Item"})

	def test_url_safety(self):
		for url in ("https://a.com/x", "http://a.com", "/app/user"):
			self.assertTrue(is_safe_url(url), url)
		for url in (
			"javascript:alert(1)",
			"data:text/html,x",
			"//evil.com",
			"ftp://a.com",
			"",
			"https://",
			"/\\evil.com",
		):
			self.assertFalse(is_safe_url(url), url)

	def test_icon_and_order_validation(self):
		self._assert_invalid({"icon": "bad icon!"})
		self._assert_invalid({"icon": "users", "order": -1})
		self._assert_valid({"icon": "users", "order": 1})

	def test_disabled_invalid_item_can_be_saved(self):
		self._assert_valid({"label": "Draft", "link_to": "", "enabled": 0})
