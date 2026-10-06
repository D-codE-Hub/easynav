import frappe
from frappe.tests import IntegrationTestCase

from easynav.api.navigation import build_navigation
from easynav.easynav.validation import MAX_ITEMS

DOCTYPE = "EasyNav User Navigation"
# the tests create their own users; User test records pull in fixtures of unrelated apps
IGNORE_TEST_RECORD_DEPENDENCIES = ["User"]


def make_user(email: str, roles: list[str]):
	if frappe.db.exists("User", email):
		user = frappe.get_doc("User", email)
	else:
		user = frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}
		).insert(ignore_permissions=True)
	user.roles = []
	for role in roles:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)
		user.append("roles", {"role": role})
	user.save(ignore_permissions=True)
	return email


def _url_item(label: str) -> dict:
	return {"label": label, "type": "URL", "url": "https://example.com"}


def make_navigation(user: str, items: list[dict] | None = None):
	"""Replace the user's shortcuts. Must run as a support user, who may save for anyone."""
	frappe.delete_doc(DOCTYPE, user, ignore_permissions=True, ignore_missing=True)
	return frappe.get_doc({"doctype": DOCTYPE, "user": user, "items": items or []}).insert(
		ignore_permissions=True
	)


class TestEasyNavUserNavigation(IntegrationTestCase):
	"""Every user owns exactly one list of shortcuts; only they and support users can reach it."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		# any desk role makes these System Users, which gives them the automatic Desk User role
		cls.user_a = make_user("easynav-a@example.com", ["Script Manager"])
		cls.user_b = make_user("easynav-b@example.com", ["Script Manager"])
		cls.manager = make_user("easynav-manager@example.com", ["System Manager"])

	def setUp(self):
		frappe.set_user("Administrator")
		make_navigation(self.user_a, [_url_item("A1")])
		make_navigation(self.user_b, [_url_item("B1")])

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_named_after_user_and_unique(self):
		self.assertEqual(frappe.get_doc(DOCTYPE, self.user_a).name, self.user_a)
		with self.assertRaises(frappe.DuplicateEntryError):
			frappe.get_doc({"doctype": DOCTYPE, "user": self.user_a}).insert()

	def test_owner_can_edit_own(self):
		frappe.set_user(self.user_a)
		doc = frappe.get_doc(DOCTYPE, self.user_a)
		doc.check_permission("read")
		doc.append("items", _url_item("A2"))
		doc.save()
		self.assertEqual([row.label for row in doc.reload().items], ["A1", "A2"])

	def test_user_cannot_reach_another_users_document(self):
		frappe.set_user(self.user_a)
		doc = frappe.get_doc(DOCTYPE, self.user_b)
		for ptype in ("read", "write", "delete"):
			self.assertFalse(frappe.has_permission(DOCTYPE, ptype, doc=doc), ptype)

		doc.append("items", _url_item("hijack"))
		self.assertRaises(frappe.PermissionError, doc.save)
		self.assertRaises(frappe.PermissionError, frappe.delete_doc, DOCTYPE, self.user_b)

	def test_list_shows_only_own_row(self):
		frappe.set_user(self.user_a)
		self.assertEqual(frappe.get_list(DOCTYPE, pluck="name"), [self.user_a])

	def test_user_cannot_create_or_delete(self):
		frappe.set_user(self.user_a)
		self.assertFalse(frappe.has_permission(DOCTYPE, "create"))
		self.assertFalse(frappe.has_permission(DOCTYPE, "delete", doc=frappe.get_doc(DOCTYPE, self.user_a)))

	def test_ownership_guard_holds_without_permission_checks(self):
		frappe.set_user(self.user_a)
		doc = frappe.get_doc(DOCTYPE, self.user_b)
		doc.append("items", _url_item("hijack"))
		with self.assertRaises(frappe.PermissionError):
			doc.save(ignore_permissions=True)

		frappe.delete_doc(DOCTYPE, self.manager, ignore_permissions=True, ignore_missing=True)
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc({"doctype": DOCTYPE, "user": self.manager}).insert(ignore_permissions=True)

	def test_user_cannot_be_reassigned(self):
		frappe.delete_doc(DOCTYPE, self.manager, ignore_permissions=True, ignore_missing=True)
		doc = frappe.get_doc(DOCTYPE, self.user_a)
		doc.user = self.manager
		# `user` is read only: Frappe restores the stored value instead of saving the change
		doc.save()
		self.assertEqual(doc.reload().user, self.user_a)
		self.assertFalse(frappe.db.exists(DOCTYPE, self.manager))

	def test_system_manager_can_view_and_fix_any_list(self):
		frappe.set_user(self.manager)
		names = frappe.get_list(DOCTYPE, pluck="name")
		self.assertIn(self.user_a, names)
		self.assertIn(self.user_b, names)

		doc = frappe.get_doc(DOCTYPE, self.user_b)
		doc.items = []
		doc.append("items", _url_item("Fixed"))
		doc.save()
		self.assertEqual([row.label for row in doc.reload().items], ["Fixed"])
		self.assertTrue(frappe.has_permission(DOCTYPE, "delete", doc=doc))
		self.assertFalse(frappe.has_permission(DOCTYPE, "create"))

	def test_system_manager_cannot_create_a_list_for_someone_else(self):
		frappe.set_user("Administrator")
		frappe.delete_doc(DOCTYPE, self.user_a, ignore_permissions=True)

		frappe.set_user(self.manager)
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc({"doctype": DOCTYPE, "user": self.user_a}).insert()
		self.assertFalse(frappe.db.exists(DOCTYPE, self.user_a))

	def test_fixing_a_list_does_not_change_the_fixers_menu(self):
		make_navigation(self.manager, [_url_item("M1")])

		frappe.set_user(self.manager)
		doc = frappe.get_doc(DOCTYPE, self.user_b)
		doc.append("items", _url_item("B2"))
		doc.save()
		self.assertEqual([i["label"] for i in build_navigation()["items"]], ["M1"])

		frappe.set_user(self.user_b)
		self.assertEqual([i["label"] for i in build_navigation()["items"]], ["B1", "B2"])

	def test_item_limit(self):
		doc = frappe.get_doc(DOCTYPE, self.user_a)
		doc.items = []
		for i in range(MAX_ITEMS):
			doc.append("items", _url_item(f"Item {i}"))
		doc.save()

		doc.append("items", _url_item("One too many"))
		self.assertRaises(frappe.ValidationError, doc.save)

	def test_items_are_validated(self):
		doc = frappe.get_doc(DOCTYPE, self.user_a)
		doc.append("items", {"label": "Bad", "type": "URL", "url": "javascript:alert(1)"})
		self.assertRaises(frappe.ValidationError, doc.save)

		# disabled rows are not validated, as before
		doc.reload()
		doc.append("items", {"enabled": 0, "label": "Bad", "type": "URL", "url": "javascript:alert(1)"})
		doc.save()

	def test_save_clears_only_the_owners_boot_cache(self):
		for user in (self.user_a, self.user_b):
			frappe.cache.hset("bootinfo", user, {"stale": 1})

		frappe.set_user(self.manager)
		frappe.get_doc(DOCTYPE, self.user_b).save()

		self.assertIsNone(frappe.cache.hget("bootinfo", self.user_b))
		self.assertEqual(frappe.cache.hget("bootinfo", self.user_a), {"stale": 1})
		frappe.cache.hdel("bootinfo", self.user_a)

	def test_follows_user_rename_and_delete(self):
		email, renamed = "easynav-temp@example.com", "easynav-renamed@example.com"
		for name in (email, renamed):
			frappe.delete_doc("User", name, ignore_permissions=True, ignore_missing=True, force=True)
		make_user(email, ["Script Manager"])
		make_navigation(email, [_url_item("T1")])

		frappe.rename_doc("User", email, renamed, force=True)
		self.assertFalse(frappe.db.exists(DOCTYPE, email))
		doc = frappe.get_doc(DOCTYPE, renamed)
		self.assertEqual((doc.user, [row.label for row in doc.items]), (renamed, ["T1"]))

		frappe.delete_doc("User", renamed)
		self.assertFalse(frappe.db.exists(DOCTYPE, renamed))
		self.assertFalse(frappe.db.exists("EasyNav Item", {"parent": renamed, "parenttype": DOCTYPE}))
