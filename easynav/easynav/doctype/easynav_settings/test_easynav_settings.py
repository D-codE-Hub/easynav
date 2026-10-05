import frappe
from frappe.tests import IntegrationTestCase

from easynav.easynav.validation import is_safe_url


class TestEasyNavSettings(IntegrationTestCase):
	def setUp(self):
		self.settings = frappe.get_doc("EasyNav Settings")
		self.settings.items = []

	def _add(self, **kw):
		row = {"label": "Item", "type": "DocType", "target": "User"}
		row.update(kw)
		self.settings.append("items", row)

	def test_valid_items(self):
		self._add()
		self._add(label="Site", type="URL", target="https://example.com")
		self.settings.save()

	def test_missing_target_and_label(self):
		self._add(target="")
		self.assertRaises(frappe.ValidationError, self.settings.save)
		self.settings.items = []
		self._add(label=" ")
		self.assertRaises(frappe.ValidationError, self.settings.save)

	def test_missing_records(self):
		for type_ in ("DocType", "Page", "Report"):
			self.settings.items = []
			self._add(type=type_, target="Does Not Exist 123")
			self.assertRaises(frappe.ValidationError, self.settings.save)

	def test_child_table_rejected(self):
		self._add(target="EasyNav Item")
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
		self._add(label="Draft", target="", enabled=0)
		self.settings.save()
