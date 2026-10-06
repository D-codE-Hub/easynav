import frappe
from frappe.tests import IntegrationTestCase

from easynav.easynav.validation import is_safe_url


class TestEasyNavSettings(IntegrationTestCase):
	def setUp(self):
		self.settings = frappe.get_doc("EasyNav Settings")
		self.settings.items = []

	def _add(self, **kw):
		row = {"label": "Item", "type": "DocType", "link_to": "User"}
		row.update(kw)
		self.settings.append("items", row)

	def test_valid_items(self):
		self._add()
		self._add(label="Site", type="URL", link_to=None, url="https://example.com")
		self.settings.save()

	def test_missing_target_and_label(self):
		self._add(link_to="")
		self.assertRaises(frappe.ValidationError, self.settings.save)
		self.settings.items = []
		self._add(label=" ")
		self.assertRaises(frappe.ValidationError, self.settings.save)

	def test_missing_records(self):
		for type_ in ("DocType", "Page", "Report", "Dashboard"):
			self.settings.items = []
			self._add(type=type_, link_to="Does Not Exist 123")
			self.assertRaises(frappe.ValidationError, self.settings.save)

	def test_url_items_use_url_field(self):
		# the address must come from `url`; a URL item without one is invalid
		self._add(label="Site", type="URL", link_to=None)
		self.assertRaises(frappe.ValidationError, self.settings.save)
		self.settings.items = []
		self._add(label="Site", type="URL", link_to=None, url="javascript:alert(1)")
		self.assertRaises(frappe.ValidationError, self.settings.save)

	def test_doc_view_validation(self):
		self._add(doc_view="Tree")  # User is not a tree DocType
		self.assertRaises(frappe.ValidationError, self.settings.save)
		self.settings = frappe.get_doc("EasyNav Settings")
		self.settings.items = []
		self._add(doc_view="Report Builder")
		self._add(link_to="System Settings", doc_view="Tree")  # ignored for Single DocTypes
		self.settings.save()

	def test_child_table_rejected(self):
		self._add(link_to="EasyNav Item")
		self.assertRaises(frappe.ValidationError, self.settings.save)

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
		self._add(icon="bad icon!")
		self.assertRaises(frappe.ValidationError, self.settings.save)
		self.settings.items = []
		self._add(icon="users", order=-1)
		self.assertRaises(frappe.ValidationError, self.settings.save)
		self.settings = frappe.get_doc("EasyNav Settings")
		self.settings.items = []
		self._add(icon="users", order=1)
		self.settings.save()

	def test_disabled_invalid_item_can_be_saved(self):
		self._add(label="Draft", link_to="", enabled=0)
		self.settings.save()
