# """
# Web browser tool split into two tiers:

#   1. FREE tools -- navigate, search, read, click links, scroll. The agent
#      can call these anytime to explore the internet on the user's behalf.

#   2. GATED tools -- anything that changes state on a real site: submitting
#      a form, clicking a Post/Buy/Follow/Like/Send/Delete-style button.
#      These REQUIRE confirmed_by_user=True, and the docstring instructs the
#      agent it must have actually asked the user and gotten a real "yes" in
#      the conversation before ever passing True. This mirrors how you
#      (Claude) are expected to confirm before sending/modifying/deleting
#      anything on a user's behalf.

# This does not make it impossible for a model to lie about confirmation --
# that's a prompting/trust boundary, not a code one. What the code DOES
# guarantee is that a gated action can never fire silently as a side effect
# of "just browsing" -- confirmed_by_user defaults to False, so the agent has
# to deliberately flip it, which is your enforcement point in logs/testing.

# SETUP:
#     pip install playwright
#     playwright install chromium
# """

# import queue
# import threading
# import time
# from langchain_core.tools import tool

# try:
#     from playwright.sync_api import sync_playwright
#     HAS_PLAYWRIGHT = True
# except ImportError:
#     HAS_PLAYWRIGHT = False


# PROFILE_DIR = "./browser_profile"
# DEFAULT_TIMEOUT_MS = 8000
# CALL_TIMEOUT_S = 30


# class _BrowserWorker:
#     """Runs every Playwright call on one dedicated thread via a request
#     queue. Playwright's sync API must stay on the thread that started it --
#     this makes that true regardless of which thread the agent calls
#     the tool functions from."""

#     def __init__(self):
#         self._queue = queue.Queue()
#         self._playwright = None
#         self._browser = None
#         self._page = None
#         self._ready = threading.Event()
#         self._thread = threading.Thread(target=self._run, daemon=True)
#         self._thread.start()
#         self._ready.wait(timeout=CALL_TIMEOUT_S)

#     def _run(self):
#         self._playwright = sync_playwright().start()
#         self._ready.set()
#         while True:
#             func, args, kwargs, result_box, done = self._queue.get()
#             try:
#                 result_box["value"] = func(self, *args, **kwargs)
#             except Exception as e:
#                 result_box["error"] = e
#             done.set()

#     def call(self, func, *args, **kwargs):
#         result_box = {}
#         done = threading.Event()
#         self._queue.put((func, args, kwargs, result_box, done))
#         if not done.wait(timeout=CALL_TIMEOUT_S):
#             raise TimeoutError("Browser operation timed out.")
#         if "error" in result_box:
#             raise result_box["error"]
#         return result_box.get("value")

#     def _ensure_page(self):
#         if self._page is None:
#             self._browser = self._playwright.chromium.launch_persistent_context(
#                 PROFILE_DIR, headless=False
#             )
#             self._page = self._browser.pages[0] if self._browser.pages else self._browser.new_page()
#         return self._page

#     def _op_navigate(self, url):
#         page = self._ensure_page()
#         page.goto(url, timeout=DEFAULT_TIMEOUT_MS)
#         return page.title()

#     def _op_click_link(self, text, exact):
#         page = self._ensure_page()
#         locator = page.get_by_role("link", name=text, exact=exact).first
#         if locator.count() == 0:
#             locator = page.get_by_text(text, exact=exact).first
#         locator.click(timeout=DEFAULT_TIMEOUT_MS)
#         return page.title()

#     def _op_read_text(self):
#         page = self._ensure_page()
#         return page.inner_text("body")[:4000]

#     def _op_scroll(self, direction):
#         page = self._ensure_page()
#         page.mouse.wheel(0, 800 if direction == "down" else -800)
#         return True

#     def _op_click_action(self, text, exact):
#         page = self._ensure_page()
#         locator = page.get_by_role("button", name=text, exact=exact).first
#         if locator.count() == 0:
#             locator = page.get_by_text(text, exact=exact).first
#         locator.click(timeout=DEFAULT_TIMEOUT_MS)
#         return True

#     def _op_fill_and_submit(self, fields, submit_text):
#         page = self._ensure_page()
#         for label, value in fields.items():
#             locator = page.get_by_placeholder(label).first
#             if locator.count() == 0:
#                 locator = page.get_by_label(label).first
#             locator.fill(value, timeout=DEFAULT_TIMEOUT_MS)
#         submit = page.get_by_role("button", name=submit_text).first
#         submit.click(timeout=DEFAULT_TIMEOUT_MS)
#         return True

#     def _op_close(self):
#         if self._browser is not None:
#             self._browser.close()
#             self._browser = None
#             self._page = None
#         return True


# _worker = None
# _worker_lock = threading.Lock()


# def _get_worker():
#     global _worker
#     with _worker_lock:
#         if _worker is None:
#             _worker = _BrowserWorker()
#         return _worker


# # ======================= FREE TOOLS (read-only) =======================

# @tool
# def navigate(url: str) -> str:
#     """Opens (or reuses) a persistent browser window and navigates to a
#     URL. Safe to call anytime -- purely navigational, changes nothing on
#     the destination site.

#     Args:
#         url: Full URL to visit.
#     """
#     if not HAS_PLAYWRIGHT:
#         return "❌ Playwright not installed. Run: pip install playwright && playwright install chromium"
#     try:
#         title = _get_worker().call(_BrowserWorker._op_navigate, url)
#         return f"✅ Navigated to {url}\nPage title: {title}"
#     except Exception as e:
#         return f"❌ Error navigating to '{url}': {e}"


# @tool
# def search_web(query: str) -> str:
#     """Runs a Google search. Safe to call anytime.

#     Args:
#         query: The search query.
#     """
#     if not HAS_PLAYWRIGHT:
#         return "❌ Playwright not installed. Run: pip install playwright && playwright install chromium"
#     try:
#         url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
#         title = _get_worker().call(_BrowserWorker._op_navigate, url)
#         return f"✅ Searched for '{query}'\nResults page: {title}"
#     except Exception as e:
#         return f"❌ Error searching for '{query}': {e}"


# @tool
# def click_link(text: str, exact: bool = False) -> str:
#     """Clicks a LINK (not a form/action button) to browse further -- e.g. a
#     search result title, an article headline, a navigation menu item. Safe
#     to call anytime, since links only navigate; they don't submit,
#     purchase, post, or delete anything.

#     Args:
#         text: Visible text of the link.
#         exact: If True, requires an exact match.
#     """
#     if not HAS_PLAYWRIGHT:
#         return "❌ Playwright not installed. Run: pip install playwright && playwright install chromium"
#     try:
#         title = _get_worker().call(_BrowserWorker._op_click_link, text, exact)
#         return f"✅ Clicked link '{text}'\nNow on: {title}"
#     except Exception as e:
#         return f"❌ Error clicking link '{text}': {e}"


# @tool
# def read_page() -> str:
#     """Reads the visible text of the current page. Safe to call anytime."""
#     if not HAS_PLAYWRIGHT:
#         return "❌ Playwright not installed. Run: pip install playwright && playwright install chromium"
#     try:
#         text = _get_worker().call(_BrowserWorker._op_read_text)
#         return text if text.strip() else "(page appears empty)"
#     except Exception as e:
#         return f"❌ Error reading page: {e}"


# @tool
# def scroll_page(direction: str = "down") -> str:
#     """Scrolls the page up or down to reveal more content. Safe to call
#     anytime.

#     Args:
#         direction: "down" or "up".
#     """
#     if not HAS_PLAYWRIGHT:
#         return "❌ Playwright not installed. Run: pip install playwright && playwright install chromium"
#     try:
#         _get_worker().call(_BrowserWorker._op_scroll, direction)
#         time.sleep(0.4)
#         return f"✅ Scrolled {direction}."
#     except Exception as e:
#         return f"❌ Error scrolling: {e}"


# @tool
# def close_browser() -> str:
#     """Closes the browser window."""
#     if not HAS_PLAYWRIGHT:
#         return "❌ Playwright not installed. Run: pip install playwright && playwright install chromium"
#     try:
#         _get_worker().call(_BrowserWorker._op_close)
#         return "✅ Browser closed."
#     except Exception as e:
#         return f"❌ Error closing browser: {e}"


# # ==================== GATED TOOLS (state-changing) ====================
# # These require confirmed_by_user=True. DO NOT set this to True unless you
# # have already asked the user a direct question in your reply (e.g. "Want
# # me to go ahead and post this?") and their most recent message is a clear
# # "yes"/affirmative. Never default to True, never infer consent from
# # silence, and never re-use an old confirmation for a new action.

# @tool
# def click_action_button(text: str, confirmed_by_user: bool, exact: bool = False) -> str:
#     """Clicks a STATE-CHANGING button on the current page -- e.g. "Post",
#     "Follow", "Like", "Buy Now", "Delete", "Submit". Requires explicit user
#     confirmation; will refuse to run otherwise.

#     Args:
#         text: Visible text of the button.
#         confirmed_by_user: Must be True, and must only be set True after
#             the user explicitly agreed to this specific action in the
#             conversation. Setting this without a real "yes" from the user
#             is a policy violation, not a shortcut.
#         exact: If True, requires an exact text match.
#     """
#     if not confirmed_by_user:
#         return (
#             f"⛔ Not executed. Clicking '{text}' changes something on this "
#             f"site. Ask the user to confirm this specific action first, "
#             f"then call this tool again with confirmed_by_user=True only "
#             f"if they clearly agreed."
#         )
#     if not HAS_PLAYWRIGHT:
#         return "❌ Playwright not installed. Run: pip install playwright && playwright install chromium"
#     try:
#         _get_worker().call(_BrowserWorker._op_click_action, text, exact)
#         return f"✅ Clicked '{text}' (user-confirmed)."
#     except Exception as e:
#         return f"❌ Error clicking '{text}': {e}"


# @tool
# def fill_and_submit_form(fields: dict, submit_button_text: str, confirmed_by_user: bool) -> str:
#     """Fills out one or more form fields and submits the form. Requires
#     explicit user confirmation; will refuse to run otherwise.

#     Args:
#         fields: Mapping of field label/placeholder text to the value to
#             enter, e.g. {"Email": "a@b.com", "Message": "Hello"}.
#         submit_button_text: Visible text of the submit button, e.g. "Send",
#             "Submit", "Sign up".
#         confirmed_by_user: Must be True, and must only be set True after
#             the user explicitly agreed to submit THIS form with THIS data.
#     """
#     if not confirmed_by_user:
#         preview = ", ".join(f"{k}: {v}" for k, v in fields.items())
#         return (
#             f"⛔ Not executed. This would submit a form ({preview}) via "
#             f"'{submit_button_text}'. Ask the user to confirm the exact "
#             f"content first, then call this tool again with "
#             f"confirmed_by_user=True only if they clearly agreed."
#         )
#     if not HAS_PLAYWRIGHT:
#         return "❌ Playwright not installed. Run: pip install playwright && playwright install chromium"
#     try:
#         _get_worker().call(_BrowserWorker._op_fill_and_submit, fields, submit_button_text)
#         return f"✅ Form submitted via '{submit_button_text}' (user-confirmed)."
#     except Exception as e:
#         return f"❌ Error submitting form: {e}"