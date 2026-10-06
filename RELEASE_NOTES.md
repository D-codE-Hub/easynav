# EasyNav Release Notes

Releases are listed newest first. Neither has a git tag yet.

---

## 2.0.0 — Per-user shortcuts

Branch `feat/user-navigation-items` (based on `develop`), 2026-10-06.

EasyNav changes from one shared menu, maintained by an administrator, to a personal menu that every user builds for themselves.

### Before you upgrade

- **The shared menu is deleted.** `bench migrate` removes every item configured in EasyNav Settings, and they cannot be restored from the app. Note them down first if users will want to re-create them.
- **Everyone starts with an empty menu.** Nothing is copied to users.
- After pulling, run `bench --site <site> migrate` and `bench build --app easynav`, then have users reload Desk.

### New

- **Personal shortcuts.** Each user has their own list of menu items, held in a new DocType, **EasyNav User Navigation**. Other users cannot see or change it.
- **Edit from the button.** Right-click the floating button to open your list (press and hold on touch screens, or use the context-menu key). The button's tooltip says so, and an empty menu explains how to add the first item.
- **The button always shows.** It is visible even when you have no shortcuts yet, so there is always a way to add some.
- **Suggestions you can use.** When picking a DocType or Page for an item, only the ones you are allowed to open are suggested. Users without System Manager can now pick Pages, which was not possible before.
- **Limit of 30 items per user.**
- **Support access for System Managers.** They can view, add, change and delete any user's list from `/desk/easynav-user-navigation`. Their edits are recorded in the document history.

### Changed

- **EasyNav Settings** now holds only the site-wide options: enable switch, button label, button icon and position. The Navigation Items table is gone.
- The menu updates without a reload after you save your own list.
- Saving a list refreshes only its owner's cached Desk data, rather than clearing the cache for the whole site.
- A user's list is deleted when the user is deleted, and follows the user when they are renamed.

### Security

- A user can read and change only their own list. This is enforced by role permissions, permission hooks and a check in the document itself.
- An ordinary user can add a list only for themselves, one per user, and cannot delete it.
- Items are still filtered by Frappe permissions when the menu is built. If someone else adds an item to your list that you cannot open, you do not see it.
- No API method accepts a user id; the menu and the editor always work on the logged-in user.

### Known limitations

- The floating menu and the edit form were not checked in a browser during development. The server side is covered by 52 automated tests and a 46-step run over the HTTP API.
- The README screenshot of EasyNav Settings still shows the old Navigation Items table.

---

## 1.0.0 — Initial release (MVP)

Branch `develop`, 2026-10-05 to 2026-10-06. The code on `develop` still reports version `0.0.1`.

The first version of EasyNav: a global floating navigation button for Frappe Desk, configured without code.

### Features

- **Floating button on every Desk page** for logged-in users, with a menu of shortcuts.
- **Five item types:** DocType, Page, Report, Dashboard and URL.
- **DocType views:** List, Report Builder, Dashboard, Tree, New, Calendar, Kanban (with an optional board) and Image. Single DocTypes open their form.
- **Per-item options:** label, icon, order, open in a new tab, and an enabled switch so drafts can be kept.
- **Site-wide options in EasyNav Settings:** enable switch, button label, button icon and position (any of the four corners). System Manager only.
- **One shared menu,** configured by a System Manager in EasyNav Settings and shown to all users.

### Using the menu

- Click the button to open the menu and keep it open; hover also opens it for mouse users.
- `ArrowUp` / `ArrowDown` move through the items; `Esc`, an outside click or a second click closes the menu.
- Ctrl/Cmd-click and middle-click open an item in a new browser tab.
- The menu closes on page change, is hidden when printing, and sits behind open dialogs.
- Styling follows Frappe's theme tokens, so it matches light and dark themes, and adapts to tablet and phone screens.

### Permissions and safety

- Users see only the items they are allowed to open: read permission for DocTypes (create for the New view, report for Report Builder), allowed roles for Pages and Reports, read permission for Dashboards. URL items are shown to everyone.
- Frappe still enforces access at the destination; EasyNav only hides links that would be refused.
- Guests never see the button.
- URLs must be `http(s)://` addresses or paths on the site. `javascript:`, `data:` and similar links are rejected on save and never returned, even if they were stored another way.
- Items are validated on save: the target must exist, child-table DocTypes are rejected, the Tree view needs a tree DocType, and a Kanban board must belong to the chosen DocType.
- An item whose target is later deleted or renamed is left out of the menu, and the rest keep working.

### Requirements

- Developed and tested on Frappe `17.0.0-dev` with Python 3.14.
