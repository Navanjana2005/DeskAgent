"""Minimal browser launcher and web-search tools."""

import webbrowser
from urllib.parse import urlencode, urlparse

from langchain_core.tools import tool


@tool
def open_web_browser(url: str) -> str:
    """Open an HTTP or HTTPS URL in the user's default web browser.

    This only launches/navigates the browser; it cannot read or interact with
    the page.

    Args:
        url: The complete HTTP or HTTPS URL to open.
    """
    parsed_url = urlparse(url.strip())
    if parsed_url.scheme.lower() not in {"http", "https"} or not parsed_url.netloc:
        return "Error: provide a complete HTTP or HTTPS URL."

    try:
        opened = webbrowser.open(url.strip(), new=2)
    except Exception as error:
        return f"Could not open the browser: {type(error).__name__}: {error}"
    if not opened:
        return "The operating system did not confirm that a browser opened."
    return f"Opened URL in the default browser: {url.strip()}"


@tool
def search_web_browser(query: str) -> str:
    """Open Google search results for a query in the default web browser.

    This opens a search-results page but does not read or summarize results.

    Args:
        query: The search terms.
    """
    cleaned_query = query.strip()
    if not cleaned_query:
        return "Error: enter a search query."

    search_url = "https://www.google.com/search?" + urlencode({"q": cleaned_query})
    try:
        opened = webbrowser.open(search_url, new=2)
    except Exception as error:
        return f"Could not open browser search: {type(error).__name__}: {error}"
    if not opened:
        return "The operating system did not confirm that a browser opened."
    return f"Opened Google search results for: {cleaned_query}"
