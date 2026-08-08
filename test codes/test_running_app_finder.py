import psutil
import os

def get_running_apps():
    """
    Returns a list of running applications (foreground-type processes)
    by filtering out background/system processes.
    """
    apps = []
    for proc in psutil.process_iter(['pid', 'name', 'username']):
        try:
            # Skip system processes and background services
            if proc.info['username'] is None:
                continue
            # Filter out processes without a visible window
            if proc.info['name'] and not proc.info['name'].lower().startswith(('system', 'svchost', 'idle')):
                apps.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return apps

if __name__ == "__main__":
    # Ensure psutil is installed
    try:
        import psutil
    except ImportError:
        print("psutil not found. Install it using: pip install psutil")
        exit(1)

    running_apps = get_running_apps()

    if running_apps:
        print(f"{'PID':<8} {'Name':<30} {'User'}")
        print("-" * 60)
        for app in running_apps:
            print(f"{app['pid']:<8} {app['name']:<30} {app['username']}")
    else:
        print("No running applications found.")
