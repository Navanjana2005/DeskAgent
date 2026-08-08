# Required imports


from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import time
import sys

def main():
    # Configure Edge options (headless mode optional)
    edge_options = Options()
    edge_options.add_argument("--start-maximized")
    # Uncomment for headless mode:
    # edge_options.add_argument("--headless")

    try:
        # Path to your EdgeDriver (ensure it matches your Edge version)
        service = Service(executable_path="C:\\Program Files (x86)\\edge_driver\\msedgedriver.exe")
        driver = webdriver.Edge(service=service, options=edge_options)

        # Open a webpage
        driver.get("https://www.google.com")

        # Wait for page to load
        time.sleep(10)

        # Interact with the search box
        try:
            search_box = driver.find_element(By.NAME, "q")
            search_box.clear()
            search_box.send_keys("Python Selenium tutorial")
            search_box.send_keys(Keys.RETURN)
        except NoSuchElementException:
            print("Search box not found.")
            driver.quit()
            sys.exit(1)

        # Wait for results to load
        time.sleep(3)

        # Extract and print the first result title
        try:
            first_result = driver.find_element(By.CSS_SELECTOR, "h3")
            print("First search result:", first_result.text)
        except NoSuchElementException:
            print("No search results found.")

        # Close browser
        driver.quit()

    except TimeoutException:
        print("Page load timed out.")
    except Exception as e:
        print("Error:", e)
        sys.exit(1)

if __name__ == "__main__":
    main()
