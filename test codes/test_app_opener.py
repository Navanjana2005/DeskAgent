from AppOpener import open

def AppOpener(app_name):
    """
    Opens the specified application using the AppOpener library.

    Args:
        app_name (str): The name of the application to open.

    Returns:
        None
    """
    try:
        open(app_name)
        print(f"{app_name} has been opened successfully.")
    except Exception as e:
        print(f"An error occurred while trying to open {app_name}: {e}")