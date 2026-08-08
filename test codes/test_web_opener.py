import webbrowser

def open_webpage(url):
    """
    Opens the specified URL in the default web browser.

    Args:
        url (str): The URL of the webpage to open.
    """
    try:
        webbrowser.open(url)
        print(f"Opening {url} in the default web browser.")
    except Exception as e:
        print(f"An error occurred while trying to open the webpage: {e}")