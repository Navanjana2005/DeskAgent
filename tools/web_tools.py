"""
tools/web_tools.py
Web, research, network, and INTERACTIVE BROWSER tools.

CHANGE FROM PREVIOUS VERSION:
- web_opener (webbrowser.open, can only open a tab) is REMOVED. It could
  not click, type, or read anything back, so tasks like "book a ticket"
  or "search and click the first result" had no tool capable of doing
  them -- the agent would correctly refuse or fall back to manual
  instructions no matter how the request was phrased.
- Replaced with a Playwright-based browser: FREE tools for navigating/
  reading/clicking links, and GATED tools (require confirmed_by_user=True)
  for anything state-changing (submitting forms, clicking Buy/Post/Follow/
  Delete-style buttons). This lets the agent actually search, click
  through, and read a booking site -- and only pauses for your explicit
  go-ahead at the actual purchase/submit step, which is the correct place
  to stop, not the first step.
- API keys now come ONLY from environment variables, no hardcoded
  fallback values. Set FIRECRAWL_API_KEY and OPENWEATHER_API_KEY in a
  .env file (or your OS environment) before running.
"""

import os
import queue
import socket
import threading
import time

import psutil
import requests
from langchain_core.tools import tool

try:
    from firecrawl import Firecrawl
    _FIRECRAWL_KEY = os.getenv("FIRECRAWL_API_KEY")
    if _FIRECRAWL_KEY:
        firecrawl = Firecrawl(api_key=_FIRECRAWL_KEY)
        HAS_FIRECRAWL = True
    else:
        HAS_FIRECRAWL = False
except Exception:
    HAS_FIRECRAWL = False

try:
    import speedtest
    HAS_SPEEDTEST = True
except ImportError:
    HAS_SPEEDTEST = False

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

MAX_CHARS_PER_PAGE = 3000
PROFILE_DIR = "./browser_profile"
DEFAULT_TIMEOUT_MS = 8000
CALL_TIMEOUT_S = 30


# ─────────────────────────────────────────────────────────────────────────────
# INTERACTIVE BROWSER (Playwright, single dedicated thread)
# ─────────────────────────────────────────────────────────────────────────────

class _BrowserWorker:
    """Runs every Playwright call on one dedicated thread via a request
    queue. Playwright's sync API must stay on the thread that started it --
    this guarantees that regardless of which thread the agent framework
    calls these tool functions from."""

    def __init__(self):
        self._queue = queue.Queue()
        self._playwright = None
        self._browser = None
        self._page = None
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=CALL_TIMEOUT_S)

    def _run(self):
        self._playwright = sync_playwright().start()
        self._ready.set()
        while True:
            func, args, kwargs, result_box, done = self._queue.get()
            try:
                result_box["value"] = func(self, *args, **kwargs)
            except Exception as e:
                result_box["error"] = e
            done.set()

    def call(self, func, *args, **kwargs):
        result_box = {}
        done = threading.Event()
        self._queue.put((func, args, kwargs, result_box, done))
        if not done.wait(timeout=CALL_TIMEOUT_S):
            raise TimeoutError("Browser operation timed out.")
        if "error" in result_box:
            raise result_box["error"]
        return result_box.get("value")

    def _ensure_page(self):
        if self._page is None:
            self._browser = self._playwright.chromium.launch_persistent_context(
                PROFILE_DIR, headless=False
            )
            self._page = self._browser.pages[0] if self._browser.pages else self._browser.new_page()
        return self._page

    def _op_navigate(self, url):
        page = self._ensure_page()
        page.goto(url, timeout=DEFAULT_TIMEOUT_MS)
        return page.title()

    def _op_click_link(self, text, exact):
        page = self._ensure_page()
        locator = page.get_by_role("link", name=text, exact=exact).first
        if locator.count() == 0:
            locator = page.get_by_text(text, exact=exact).first
        locator.click(timeout=DEFAULT_TIMEOUT_MS)
        return page.title()

    def _op_read_text(self):
        page = self._ensure_page()
        return page.inner_text("body")[:4000]

    def _op_scroll(self, direction):
        page = self._ensure_page()
        page.mouse.wheel(0, 800 if direction == "down" else -800)
        return True

    def _op_click_action(self, text, exact):
        page = self._ensure_page()
        locator = page.get_by_role("button", name=text, exact=exact).first
        if locator.count() == 0:
            locator = page.get_by_text(text, exact=exact).first
        locator.click(timeout=DEFAULT_TIMEOUT_MS)
        return True

    def _op_fill_and_submit(self, fields, submit_text):
        page = self._ensure_page()
        for label, value in fields.items():
            locator = page.get_by_placeholder(label).first
            if locator.count() == 0:
                locator = page.get_by_label(label).first
            locator.fill(value, timeout=DEFAULT_TIMEOUT_MS)
        submit = page.get_by_role("button", name=submit_text).first
        submit.click(timeout=DEFAULT_TIMEOUT_MS)
        return True

    def _op_close(self):
        if self._browser is not None:
            self._browser.close()
            self._browser = None
            self._page = None
        return True


_worker = None
_worker_lock = threading.Lock()


def _get_worker():
    global _worker
    with _worker_lock:
        if _worker is None:
            _worker = _BrowserWorker()
        return _worker


@tool
def navigate(url: str) -> str:
    """Opens (or reuses) a persistent browser window and navigates to a
    URL. Use this to open any website, including for tasks like searching,
    checking, or booking things -- this is the ONLY tool that opens URLs;
    it also lets the agent read and interact with the page afterward.

    Args:
        url: Full URL to visit.
    """
    if not HAS_PLAYWRIGHT:
        return "❌ Playwright not installed. Run: pip install playwright && playwright install chromium"
    try:
        title = _get_worker().call(_BrowserWorker._op_navigate, url)
        return f"✅ Navigated to {url}\nPage title: {title}"
    except Exception as e:
        return f"❌ Error navigating to '{url}': {e}"


@tool
def search_web(query: str) -> str:
    """Runs a Google search. Safe to call anytime.

    Args:
        query: The search query.
    """
    if not HAS_PLAYWRIGHT:
        return "❌ Playwright not installed. Run: pip install playwright && playwright install chromium"
    try:
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        title = _get_worker().call(_BrowserWorker._op_navigate, url)
        return f"✅ Searched for '{query}'\nResults page: {title}"
    except Exception as e:
        return f"❌ Error searching for '{query}': {e}"


@tool
def click_link(text: str, exact: bool = False) -> str:
    """Clicks a LINK to browse further -- e.g. a search result title, an
    article headline, a "Buy tickets" link that just navigates to another
    page. Safe to call anytime; links only navigate, they don't submit,
    purchase, or delete.

    Args:
        text: Visible text of the link.
        exact: If True, requires an exact match.
    """
    if not HAS_PLAYWRIGHT:
        return "❌ Playwright not installed. Run: pip install playwright && playwright install chromium"
    try:
        title = _get_worker().call(_BrowserWorker._op_click_link, text, exact)
        return f"✅ Clicked link '{text}'\nNow on: {title}"
    except Exception as e:
        return f"❌ Error clicking link '{text}': {e}"


@tool
def read_page() -> str:
    """Reads the visible text of the current page. Call this after
    navigate()/search_web()/click_link() to see what's actually on the
    page (available showtimes, seat options, form fields, etc.) before
    deciding what to click or fill next.
    """
    if not HAS_PLAYWRIGHT:
        return "❌ Playwright not installed. Run: pip install playwright && playwright install chromium"
    try:
        text = _get_worker().call(_BrowserWorker._op_read_text)
        return text if text.strip() else "(page appears empty)"
    except Exception as e:
        return f"❌ Error reading page: {e}"


@tool
def scroll_page(direction: str = "down") -> str:
    """Scrolls the page up or down to reveal more content.

    Args:
        direction: "down" or "up".
    """
    if not HAS_PLAYWRIGHT:
        return "❌ Playwright not installed. Run: pip install playwright && playwright install chromium"
    try:
        _get_worker().call(_BrowserWorker._op_scroll, direction)
        time.sleep(0.4)
        return f"✅ Scrolled {direction}."
    except Exception as e:
        return f"❌ Error scrolling: {e}"


@tool
def close_browser() -> str:
    """Closes the browser window."""
    if not HAS_PLAYWRIGHT:
        return "❌ Playwright not installed. Run: pip install playwright && playwright install chromium"
    try:
        _get_worker().call(_BrowserWorker._op_close)
        return "✅ Browser closed."
    except Exception as e:
        return f"❌ Error closing browser: {e}"


@tool
def click_action_button(text: str, confirmed_by_user: bool, exact: bool = False) -> str:
    """Clicks a STATE-CHANGING button on the current page -- e.g. "Book
    Now", "Pay", "Follow", "Buy Now", "Delete", "Submit". This is the ONLY
    step in a booking/purchase flow that requires confirmation -- browsing,
    searching, and reading showtimes/prices first is fine without it.

    Args:
        text: Visible text of the button.
        confirmed_by_user: Must be True, and must only be set True after
            the user explicitly agreed to THIS specific action (e.g. "yes,
            book the 7pm showing") in the conversation. Never set this
            without a real "yes" from the user.
        exact: If True, requires an exact text match.
    """
    if not confirmed_by_user:
        return (
            f"⛔ Not executed. Clicking '{text}' changes something on this "
            f"site (booking, purchase, follow, delete, etc). Tell the user "
            f"exactly what this will do and ask them to confirm, then call "
            f"this tool again with confirmed_by_user=True only if they "
            f"clearly agreed."
        )
    if not HAS_PLAYWRIGHT:
        return "❌ Playwright not installed. Run: pip install playwright && playwright install chromium"
    try:
        _get_worker().call(_BrowserWorker._op_click_action, text, exact)
        return f"✅ Clicked '{text}' (user-confirmed)."
    except Exception as e:
        return f"❌ Error clicking '{text}': {e}"


@tool
def fill_and_submit_form(fields: dict, submit_button_text: str, confirmed_by_user: bool) -> str:
    """Fills out one or more form fields and submits the form (e.g. seat
    selection, payment details, sign-up forms). Requires explicit user
    confirmation of the exact data being submitted.

    Args:
        fields: Mapping of field label/placeholder text to the value to
            enter, e.g. {"Email": "a@b.com", "Card number": "..."}.
        submit_button_text: Visible text of the submit button.
        confirmed_by_user: Must be True, and must only be set True after
            the user explicitly agreed to submit THIS form with THIS data.
    """
    if not confirmed_by_user:
        preview = ", ".join(f"{k}: {v}" for k, v in fields.items())
        return (
            f"⛔ Not executed. This would submit a form ({preview}) via "
            f"'{submit_button_text}'. Show the user exactly what will be "
            f"submitted and ask them to confirm, then call this tool again "
            f"with confirmed_by_user=True only if they clearly agreed."
        )
    if not HAS_PLAYWRIGHT:
        return "❌ Playwright not installed. Run: pip install playwright && playwright install chromium"
    try:
        _get_worker().call(_BrowserWorker._op_fill_and_submit, fields, submit_button_text)
        return f"✅ Form submitted via '{submit_button_text}' (user-confirmed)."
    except Exception as e:
        return f"❌ Error submitting form: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# RESEARCH / INFO TOOLS (unchanged logic, keys now env-only)
# ─────────────────────────────────────────────────────────────────────────────

@tool
def deep_web_research(query: str, num_sources: int = 3) -> str:
    """Performs deep web research: searches the web and scrapes each result page for actual content.
    Use for synthesizing an answer from multiple sources -- NOT for interactive tasks like booking
    or purchasing, which need navigate()/click_link()/click_action_button() instead.

    Args:
        query: The search query.
        num_sources: Number of top results to scrape (default 3, max 5).
    """
    if not HAS_FIRECRAWL:
        return (
            "❌ Firecrawl not available. Install it (pip install firecrawl-py) "
            "and set FIRECRAWL_API_KEY in your environment/.env file."
        )
    num_sources = min(num_sources, 5)
    try:
        search_results = firecrawl.search(query=query, limit=num_sources)
    except Exception as e:
        return f"Search failed: {e}"

    urls = [r.url for r in search_results.web if getattr(r, "url", None)]
    if not urls:
        return f"No search results found for query: {query}"

    report_sections = []
    for url in urls:
        try:
            page = firecrawl.scrape(url=url, formats=["markdown"])
            content = (getattr(page, "markdown", None) or "").strip()
            trimmed = content[:MAX_CHARS_PER_PAGE] if content else "(No extractable content)"
            report_sections.append(f"### Source: {url}\n{trimmed}")
        except Exception as e:
            report_sections.append(f"### Source: {url}\n(Failed to scrape: {e})")

    combined = "\n\n".join(report_sections)
    return (
        f"Research results for '{query}' from {len(urls)} sources:\n\n{combined}\n\n"
        "Instruction: synthesize a clear, well-organized answer from the above sources."
    )


@tool
def get_weather(city: str) -> str:
    """Fetches current weather data for the specified city using OpenWeatherMap API.

    Args:
        city: The name of the city (e.g., 'London', 'Colombo').
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return "❌ OPENWEATHER_API_KEY not set. Add it to your environment/.env file."
    base_url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": api_key, "units": "metric"}
    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return (
            f"📍 Weather in {data['name']}, {data['sys']['country']}\n"
            f"🌡️  Temperature : {data['main']['temp']}°C (Feels like {data['main']['feels_like']}°C)\n"
            f"💧 Humidity    : {data['main']['humidity']}%\n"
            f"🌬️  Wind Speed  : {data['wind']['speed']} m/s\n"
            f"🌤️  Condition   : {data['weather'][0]['description'].capitalize()}"
        )
    except requests.exceptions.HTTPError:
        if response.status_code == 404:
            return f"❌ City '{city}' not found."
        return f"❌ HTTP error: {response.status_code}"
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def download_file(url: str, save_path: str) -> str:
    """Downloads any file from a URL and saves it locally.

    Args:
        url: Direct download link.
        save_path: Local path to save the file (e.g., './downloads/file.zip').
    """
    try:
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            downloaded = 0
            with open(save_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
        size_mb = downloaded / (1024 * 1024)
        return f"⬇️  Downloaded ({size_mb:.2f} MB)\n📁 {save_path}"
    except Exception as e:
        return f"❌ Download error: {e}"


@tool
def run_speed_test() -> str:
    """Runs an internet speed test and returns download/upload speeds and ping.
    Note: This may take 20–40 seconds to complete.
    """
    if not HAS_SPEEDTEST:
        return "❌ speedtest-cli not installed. Run: pip install speedtest-cli"
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        download_mbps = st.download() / 1_000_000
        upload_mbps = st.upload() / 1_000_000
        ping_ms = st.results.ping
        server = st.results.server["sponsor"] + " — " + st.results.server["name"]
        return (
            f"📡 Speed Test Results\n{'─' * 30}\n"
            f"⬇️  Download: {download_mbps:.2f} Mbps\n"
            f"⬆️  Upload:   {upload_mbps:.2f} Mbps\n"
            f"📶 Ping:     {ping_ms:.0f} ms\n"
            f"🖥️  Server:   {server}"
        )
    except Exception as e:
        return f"❌ Speed test failed: {e}"


@tool
def get_network_info() -> str:
    """Returns current network information: local IP, hostname, active interfaces, and MAC addresses."""
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        lines = [
            f"🌐 Network Information",
            f"{'─' * 40}",
            f"Hostname:  {hostname}",
            f"Local IP:  {local_ip}",
            f"\nNetwork Interfaces:",
        ]
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        for iface, addr_list in addrs.items():
            stat = stats.get(iface)
            status = "UP" if (stat and stat.isup) else "DOWN"
            lines.append(f"\n  {iface} [{status}]")
            for addr in addr_list:
                family = str(addr.family).replace("AddressFamily.", "")
                lines.append(f"    {family}: {addr.address}")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def get_public_ip() -> str:
    """Returns the current public IP address and basic geolocation (country, city, ISP).
    Uses the free ipinfo.io service — no API key required.
    """
    try:
        resp = requests.get("https://ipinfo.io/json", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return (
            f"🌍 Public IP Info\n"
            f"{'─' * 30}\n"
            f"IP:       {data.get('ip', 'N/A')}\n"
            f"City:     {data.get('city', 'N/A')}\n"
            f"Region:   {data.get('region', 'N/A')}\n"
            f"Country:  {data.get('country', 'N/A')}\n"
            f"Org/ISP:  {data.get('org', 'N/A')}\n"
            f"Timezone: {data.get('timezone', 'N/A')}"
        )
    except Exception as e:
        return f"❌ Error fetching public IP: {e}"


@tool
def check_website_status(url: str) -> str:
    """Checks if a website is online or offline and measures response time.

    Args:
        url: The website URL to check (e.g., 'https://google.com').
    """
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        start = time.time()
        resp = requests.get(url, timeout=10, allow_redirects=True)
        elapsed = (time.time() - start) * 1000  # ms
        status_emoji = "✅" if resp.status_code < 400 else "⚠️"
        return (
            f"{status_emoji} {url}\n"
            f"Status Code:   {resp.status_code}\n"
            f"Response Time: {elapsed:.0f} ms\n"
            f"Content-Type:  {resp.headers.get('Content-Type', 'N/A')}\n"
            f"Server:        {resp.headers.get('Server', 'N/A')}"
        )
    except requests.exceptions.ConnectionError:
        return f"❌ {url} — OFFLINE (connection refused)"
    except requests.exceptions.Timeout:
        return f"⏱️  {url} — Timed out after 10 seconds"
    except Exception as e:
        return f"❌ Error: {e}"