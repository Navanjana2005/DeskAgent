import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import tools
from tools.webbrowser_app_automation import open_web_browser, search_web_browser


class WebBrowserToolTests(unittest.TestCase):
    def test_browser_module_exposes_only_open_and_search_tools(self):
        module_tools = {
            value.name
            for value in vars(__import__(
                "tools.webbrowser_app_automation",
                fromlist=["open_web_browser"],
            )).values()
            if hasattr(value, "invoke") and hasattr(value, "name")
        }
        self.assertEqual(
            module_tools,
            {"open_web_browser", "search_web_browser"},
        )

    def test_open_browser_validates_url_before_launch(self):
        with patch("tools.webbrowser_app_automation.webbrowser.open") as open_browser:
            result = open_web_browser.invoke({"url": "javascript:alert(1)"})
        open_browser.assert_not_called()
        self.assertIn("HTTP or HTTPS", result)

    def test_open_browser_launches_valid_http_url(self):
        with patch(
            "tools.webbrowser_app_automation.webbrowser.open",
            return_value=True,
        ) as open_browser:
            result = open_web_browser.invoke({"url": "https://example.com/page"})
        open_browser.assert_called_once_with("https://example.com/page", new=2)
        self.assertIn("Opened URL", result)

    def test_search_encodes_query_and_opens_google_results(self):
        with patch(
            "tools.webbrowser_app_automation.webbrowser.open",
            return_value=True,
        ) as open_browser:
            result = search_web_browser.invoke({"query": "python langchain tools"})
        opened_url = open_browser.call_args.args[0]
        self.assertEqual(
            parse_qs(urlparse(opened_url).query),
            {"q": ["python langchain tools"]},
        )
        self.assertIn("Google search results", result)

    def test_search_rejects_empty_query(self):
        with patch("tools.webbrowser_app_automation.webbrowser.open") as open_browser:
            result = search_web_browser.invoke({"query": "  "})
        open_browser.assert_not_called()
        self.assertIn("search query", result)

    def test_tools_are_registered(self):
        names = {item.name for item in tools.get_tools()}
        self.assertIn("open_web_browser", names)
        self.assertIn("search_web_browser", names)


if __name__ == "__main__":
    unittest.main()
