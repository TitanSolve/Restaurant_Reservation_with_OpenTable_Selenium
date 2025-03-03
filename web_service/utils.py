import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from config import logger

def find_element_with_timing(driver, by, xpath, description):
    """
    Attempts to find an element with timing and logs the process.
    """
    start = time.perf_counter()
    try:
        element = driver.find_element(by, xpath)
        elapsed = time.perf_counter() - start
        logger.info("SUCCESS: Found '%s' (xpath: '%s') in %.4f seconds.", description, xpath, elapsed)
        return element
    except NoSuchElementException:
        elapsed = time.perf_counter() - start
        logger.warning("WARNING: Element '%s' (xpath: '%s') not found in %.4f seconds.", description, xpath, elapsed)
        raise
    except TimeoutException:
        elapsed = time.perf_counter() - start
        logger.error("ERROR: Timeout while searching for '%s' (xpath: '%s') after %.4f seconds.", description, xpath, elapsed)
        raise
    except Exception as e:
        elapsed = time.perf_counter() - start
        logger.critical("CRITICAL FAILURE: Unexpected error while searching for '%s' (xpath: '%s') after %.4f seconds. Error: %s",
                        description, xpath, elapsed, e, exc_info=True)
        raise

def find_elements_with_timing(driver, by, xpath, description):
    """
    Attempts to find multiple elements with timing and logs the process.
    """
    start = time.perf_counter()
    try:
        elements = driver.find_elements(by, xpath)
        elapsed = time.perf_counter() - start
        if elements:
            logger.info("SUCCESS: Found %d '%s' elements (xpath: '%s') in %.4f seconds.", len(elements), description, xpath, elapsed)
        else:
            logger.warning("WARNING: No elements found for '%s' (xpath: '%s') in %.4f seconds.", description, xpath, elapsed)
        return elements
    except NoSuchElementException:
        elapsed = time.perf_counter() - start
        logger.warning("WARNING: Elements '%s' (xpath: '%s') not found in %.4f seconds.", description, xpath, elapsed)
        return []
    except TimeoutException:
        elapsed = time.perf_counter() - start
        logger.error("ERROR: Timeout while searching for elements '%s' (xpath: '%s') after %.4f seconds.", description, xpath, elapsed)
        return []
    except Exception as e:
        elapsed = time.perf_counter() - start
        logger.critical("CRITICAL FAILURE: Unexpected error while searching for elements '%s' (xpath: '%s') after %.4f seconds. Error: %s",
                        description, xpath, elapsed, e, exc_info=True)
        raise

def convert_to_am_pm(hour: int, minute: int) -> str:
    """
    Converts 24-hour time to 12-hour AM/PM format.
    """
    if not isinstance(hour, int) or not (0 <= hour < 24):
        logger.error("Invalid hour: %s. Must be between 0 and 23.", hour)
        raise ValueError(f"Invalid hour {hour}. Must be between 0 and 23.")
    
    if not isinstance(minute, int) or not (0 <= minute < 60):
        logger.error("Invalid minute: %s. Must be between 0 and 59.", minute)
        raise ValueError(f"Invalid minute {minute}. Must be between 0 and 59.")

    am_pm_time = (
        f"12:{minute:02d} am" if hour == 0 else
        f"{hour}:{minute:02d} am" if hour < 12 else
        f"12:{minute:02d} pm" if hour == 12 else
        f"{hour - 12}:{minute:02d} pm"
    )
    logger.info("Converted time: %02d:%02d -> %s", hour, minute, am_pm_time)
    return am_pm_time

def validate_date(date_str: str, fmt: str = "%Y-%m-%d"):
    """
    Validates whether a given date string matches the expected format.
    """
    try:
        datetime.strptime(date_str, fmt)
        logger.info("Date validation successful: '%s' matches format '%s'.", date_str, fmt)
    except ValueError as e:
        logger.error("Invalid date '%s'. Expected format '%s'. Error: %s", date_str, fmt, e)
        raise ValueError(f"Invalid date '{date_str}'. Expected format {fmt}. Error: {e}")

def validate_reservation_date(date: str, hour: int, minute: int) -> bool:
    """
    Validates whether the given date and time is in the future.
    """
    input_datetime = datetime.strptime(date, "%Y-%m-%d").replace(hour=hour, minute=minute)
    now = datetime.now()
    return input_datetime > now
