import frappe
from frappe.desk.search import search_widget
from frappe.tests import IntegrationTestCase

from easynav.api.navigation import build_navigation
from easynav.api.search import search_targets
from easynav.easynav.doctype.easynav_user_navigation.test_easynav_user_navigation import (
	make_navigation,
	make_user,
)

DOCTYPE = "EasyNav User Navigation"
QUERY = "easynav.api.search.search_targets"
IGNORE_TEST_RECORD_DEPENDENCIES = ["User"]
ALL = 10**6


def _names(doctype: str, txt: str = "", page_len: int = ALL) -> list[str]:
	return [row[0] for row in search_targets(doctype, txt, "name", 0, page_len, {})]


class TestTargetSearch(IntegrationTestCase):
	"""A user without System Manager must be able to build their list on their own."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.user = make_user("easynav-a@example.com", ["Script Manager"])

		if not frappe.db.exists("Dashboard", "EasyNav Test Dashboard"):
			frappe.get_doc({"doctype": "Dashboard", "dashboard_name": "EasyNav Test Dashboard"}).insert()
		if not frappe.db.exists("Kanban Board", "EasyNav Test Board"):
			frappe.get_doc(
				{
					"doctype": "Kanban Board",
					"kanban_board_name": "EasyNav Test Board",
					"reference_doctype": "ToDo",
					"field_name": "status",
					"columns": [{"column_name": "Open"}, {"column_name": "Closed"}],
				}
			).insert()
		if not frappe.db.exists("Report", "EasyNav Open Report"):
			frappe.get_doc(
				{
					"doctype": "Report",
					"report_name": "EasyNav Open Report",
					"ref_doctype": "ToDo",
					"report_type": "Report Builder",
					"is_standard": "No",
					"roles": [{"role": "Desk User"}],
				}
			).insert()

	def setUp(self):
		frappe.set_user("Administrator")
		settings = frappe.get_doc("EasyNav Settings")
		settings.enabled = 1
		settings.save()
		make_navigation(self.user)
		frappe.set_user(self.user)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_doctypes_are_limited_to_what_the_user_can_read(self):
		names = _names("DocType")
		self.assertIn("ToDo", names)
		self.assertIn("Server Script", names)
		self.assertNotIn("System Settings", names)
		self.assertNotIn("EasyNav Item", names)  # child tables cannot be opened
		for name in names:
			self.assertTrue(frappe.has_permission(name, "read"), name)

		frappe.set_user("Administrator")
		self.assertIn("System Settings", _names("DocType"))
		self.assertNotIn("EasyNav Item", _names("DocType"))

	def test_pages_are_limited_to_permitted_ones(self):
		restricted = "workflow-builder"  # System Manager only
		names = _names("Page")
		self.assertTrue(names)
		self.assertNotIn(restricted, names)
		for name in names:
			self.assertTrue(frappe.get_doc("Page", name).is_permitted(), name)

		frappe.set_user("Administrator")
		self.assertIn(restricted, _names("Page"))

	def test_text_filter_and_paging(self):
		self.assertEqual(_names("DocType", "Server Scr"), ["Server Script"])
		everything = _names("DocType")
		self.assertEqual(_names("DocType", page_len=3), everything[:3])
		self.assertEqual([row[0] for row in search_targets("DocType", "", "name", 2, 3, {})], everything[2:5])

	def test_other_doctypes_are_not_searchable(self):
		self.assertEqual(_names("User"), [])
		self.assertEqual(_names("Does Not Exist 123"), [])

	def test_works_as_link_query(self):
		"""The form calls it through Frappe's link search, for suggestions and to validate a pick."""
		self.assertIn(["ToDo"], [list(row) for row in search_widget("DocType", "ToD", query=QUERY)])

		def is_valid(doctype, name):
			rows = search_widget(doctype, name, query=QUERY, page_length=0, for_link_validation=True)
			return any(row[0] == name for row in rows)

		page = _names("Page")[0]
		self.assertTrue(is_valid("DocType", "ToDo"))
		self.assertTrue(is_valid("Page", page))
		self.assertFalse(is_valid("DocType", "System Settings"))
		self.assertFalse(is_valid("Page", "workflow-builder"))

	def test_user_can_save_one_item_of_each_type(self):
		page = _names("Page")[0]
		doc = frappe.get_doc(DOCTYPE, self.user)
		for row in (
			{"label": "DocType", "type": "DocType", "link_to": "ToDo"},
			{"label": "Kanban", "type": "DocType", "link_to": "ToDo", "doc_view": "Kanban"}
			| {"kanban_board": "EasyNav Test Board"},
			{"label": "Page", "type": "Page", "link_to": page},
			{"label": "Report", "type": "Report", "link_to": "EasyNav Open Report"},
			{"label": "Dashboard", "type": "Dashboard", "link_to": "EasyNav Test Dashboard"},
			{"label": "URL", "type": "URL", "url": "/app/todo"},
		):
			doc.append("items", row)
		doc.save()

		labels = [item["label"] for item in build_navigation()["items"]]
		self.assertEqual(labels, ["DocType", "Kanban", "Page", "Report", "Dashboard", "URL"])
