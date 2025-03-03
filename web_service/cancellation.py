import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from config import logger
from driver import setup_driver

def cancel_reservation(
    cancel_url: str = "",
    browser_url: str = "",
    proxy_host: str = None,
    proxy_port: int = None,
    proxy_username: str = None,
    proxy_password: str = None,
    proxy_scheme: str = "http",
):
    overall_start = time.perf_counter()
    logger.info("Starting cancelling process...")
    
    try:
        driver = setup_driver(browser_url, proxy_host, proxy_port, proxy_username, proxy_password, proxy_scheme)
        logger.info("WebDriver initialized successfully.")
    except Exception as e:
        logger.exception("WebDriver initialization failed.")
        return (False, f"WebDriver error: {e}")

    logger.info("Starting booking process. Navigating to cancelling URL: %s", cancel_url)
    start = time.perf_counter()
    try:
        driver.get(cancel_url)
    except Exception as e:
        logger.exception("WebDriver failed to navigate to cancelling URL: %s", cancel_url)
        return (False, f"WebDriver error: {e}")
    
    elapsed = time.perf_counter() - start
    logger.info("Cancel page loaded in %.4f seconds", elapsed)
    
    try:
        cancel_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@data-button='true' and .//span[normalize-space()='Cancel']]")),
        )
        elapsed = time.perf_counter() - start
        logger.info("Cancel button became visible in %.4f seconds", elapsed)
        cancel_button.click()
        logger.info("The cancel button is clicked")
    except TimeoutException:
        elapsed = time.perf_counter() - overall_start
        logger.error("Cancel button did not appear after %.4f seconds", elapsed)
        return (False, "Cancel button did not appear.")
    except Exception as e:
        logger.exception("Unexpected error while waiting for time slot elements: %s", str(e))
        return (False, f"Unexpected error: {str(e)}")
    
    try:
        cancel_reservation_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@data-button='true' and .//span[normalize-space()='Cancel reservation']]")),
        )
        elapsed = time.perf_counter() - start
        logger.info("Cancel reservation button became visible in %.4f seconds", elapsed)
        cancel_reservation_button.click()
        logger.info("The cancel_reservation button is clicked")
    except TimeoutException:
        elapsed = time.perf_counter() - overall_start
        logger.error("Cancel reservation button did not appear after %.4f seconds", elapsed)
        return (False, "Cancel reservation button did not appear.")
    except Exception as e:
        logger.exception("Unexpected error while waiting for time slot elements: %s", str(e))
        return (False, f"Unexpected error: {str(e)}")
    
    try:
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Your reservation has been canceled!')]"))
        )
        elapsed = time.perf_counter() - start
        logger.info("Cancel reservation message became visible in %.4f seconds", elapsed)
        return (True, "The requested reservation is cancelled")
    except TimeoutException:
        elapsed = time.perf_counter() - overall_start
        logger.error("Cancel reservation message did not appear after %.4f seconds", elapsed)
        return (False, "Cancel reservation message did not appear.")
    except Exception as e:
        logger.exception("Unexpected error while waiting for time slot elements: %s", str(e))
        return (False, f"Unexpected error: {str(e)}")
