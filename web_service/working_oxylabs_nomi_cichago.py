#!/usr/bin/env python3
import logging
import time
import random
import string
import tempfile
import zipfile
import pytz
from datetime import datetime
from zoneinfo import ZoneInfo
from logging.handlers import RotatingFileHandler
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, InvalidElementStateException
from selenium import webdriver
from selenium.webdriver.common.keys import Keys

# Define Mexico City timezone
MEXICO_TZ = pytz.timezone("America/Mexico_City")

class MexicoTimeFormatter(logging.Formatter):
    """Custom formatter to log times in Mexico City time zone."""
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=MEXICO_TZ)
        return dt.strftime(datefmt or "%Y-%m-%d %H:%M:%S %Z")
    
def get_ordinal_suffix(day: int) -> str:
    """Returns the ordinal suffix for a given day."""
    if 11 <= day <= 13:  # Handle 11th, 12th, 13th as special cases
        return "th"
    last_digit = day % 10
    return {1: "st", 2: "nd", 3: "rd"}.get(last_digit, "th")

# Log format and date format
log_format = "%(asctime)s %(levelname)s: %(message)s"
date_format = "%Y-%m-%d %H:%M:%S %Z"

# Create log file handler with rotation (5MB per file, keeping last 3 logs)
log_file = "app.log"
file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)
file_formatter = MexicoTimeFormatter(fmt=log_format, datefmt=date_format)
file_handler.setFormatter(file_formatter)

# Create console handler
console_handler = logging.StreamHandler()
console_formatter = MexicoTimeFormatter(fmt=log_format, datefmt=date_format)
console_handler.setFormatter(console_formatter)

# Configure root logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Change to DEBUG for detailed logs
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Example log to test
logger.info("This log should show Mexico City time.")

def generate_random_email():
    domains = ["gmail.com", "yahoo.com", "outlook.com", "example.com"]
    
    username_length = random.randint(8, 12)
    username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=username_length))

    domain = random.choice(domains)    
    return f"{username}@{domain}"

def time_difference_in_minutes(time1, time2):
    fmt = "%I:%M %p"
    t1 = datetime.strptime(time1, fmt)
    t2 = datetime.strptime(time2, fmt)

    diff = abs((t2 - t1).total_seconds()) // 60
    return int(diff)

def create_proxy_auth_extension(proxy_host, proxy_port, proxy_username, proxy_password, scheme='http'):
    """
    Creates a Chrome extension (as a .zip file) to handle proxy authentication.
    Returns the file path to the generated extension.
    """
    try:
        logger.info("Starting proxy authentication extension creation.")

        manifest_json = """
        {
            "version": "1.0.0",
            "manifest_version": 2,
            "name": "Chrome Proxy",
            "permissions": [
                "proxy",
                "tabs",
                "unlimitedStorage",
                "storage",
                "<all_urls>",
                "webRequest",
                "webRequestBlocking"
            ],
            "background": {
                "scripts": ["background.js"]
            }
        }
        """
        background_js = f"""
        var config = {{
            mode: "fixed_servers",
            rules: {{
              singleProxy: {{
                scheme: "{scheme}",
                host: "{proxy_host}",
                port: parseInt({proxy_port})
              }},
              bypassList: ["localhost"]
            }}
          }};

        chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});

        function callbackFn(details) {{
            return {{
                authCredentials: {{
                    username: "{proxy_username}",
                    password: "{proxy_password}"
                }}
            }};
        }}

        chrome.webRequest.onAuthRequired.addListener(
            callbackFn,
            {{urls: ["<all_urls>"]}},
            ["blocking"]
        );
        """

        plugin_file = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)

        with zipfile.ZipFile(plugin_file, 'w') as zp:
            zp.writestr("manifest.json", manifest_json.strip())
            zp.writestr("background.js", background_js.strip())

        plugin_file.close()

        logger.info("Successfully created proxy authentication extension at: %s", plugin_file.name)
        return plugin_file.name

    except Exception as e:
        logger.critical("Failed to create proxy authentication extension: %s", e, exc_info=True)
        return None

def setup_driver(browser_url="",
                 proxy_host=None,
                 proxy_port=None,
                 proxy_username=None,
                 proxy_password=None,
                 proxy_scheme="http"):
    """
    Initialize a Chrome webdriver with options optimized for speed.
    If proxy settings are provided (using Oxylabs), the proxy is configured.
    """
    logger.info("Starting driver setup.")

    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.page_load_strategy = "eager"

    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.stylesheets": 2,
        "profile.managed_default_content_settings.fonts": 2,
        "profile.managed_default_content_settings.plugins": 2,
    }
    options.add_experimental_option("prefs", prefs)

    # Configure proxy if details are provided
    if proxy_host and proxy_port:
        try:
            if proxy_username and proxy_password:
                proxy_extension = create_proxy_auth_extension(proxy_host, proxy_port, proxy_username, proxy_password, scheme=proxy_scheme)
                options.add_extension(proxy_extension)
                logger.info("Using proxy authentication extension for %s:%s", proxy_host, proxy_port)
            else:
                options.add_argument(f"--proxy-server={proxy_scheme}://{proxy_host}:{proxy_port}")
                logger.info("Configured proxy: %s:%s using scheme %s", proxy_host, proxy_port, proxy_scheme)
        except Exception as e:
            logger.critical("Failed to configure proxy: %s", e, exc_info=True)
            raise

    # Initialize WebDriver
    try:
        if browser_url:
            logger.info("Initializing remote WebDriver at URL: %s", browser_url)
            driver = webdriver.Remote(command_executor=browser_url, options=options)
        else:
            logger.info("Initializing local Chrome WebDriver.")
            driver = webdriver.Chrome(options=options)
        logger.info("WebDriver initialized successfully.")
    except WebDriverException as e:
        logger.critical("WebDriver initialization failed.", exc_info=True)
        raise e

    # Configure Chrome DevTools Protocol (CDP) to block unnecessary resources
    try:
        driver.execute_cdp_cmd("Network.enable", {})
        driver.execute_cdp_cmd(
            "Network.setBlockedURLs",
            {"urls": [
                "*googleapis.com/maps*",
                "*googleapis.com/vt?*",
                "*maps.gstatic.com*",
                "*.jpg", "*.jpeg", "*.png", "*.gif",
                "*.css", "*.woff", "*.woff2", "*.ttf",
                "*google-analytics.com*", "*adservice.google.com*",
                "*doubleclick.net*", "*facebook.net*"
            ]}
        )
        logger.info("CDP block list configured successfully.")
    except Exception as e:
        logger.warning("Error setting CDP block list: %s", e, exc_info=True)

    driver.set_page_load_timeout(20)
    # try:
    #     logger.info("Checking public IP address...")
    #     driver.get("https://api.ipify.org")
    #     ip_address = driver.find_element(By.TAG_NAME, "body").text
    #     logger.info("Public IP address: %s", ip_address)
    # except Exception as e:
    #     logger.error("Failed to retrieve public IP address: %s", e)
    logger.info("WebDriver setup completed successfully.")
    return driver

def find_element_with_timing(driver, by, xpath, description):
    """
    Attempts to find an element with timing and detailed logging.
    
    Logs the time taken and whether the search was successful or failed.
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
    Attempts to find multiple elements with timing and detailed logging.
    
    Logs the time taken and whether the search was successful or failed.
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
    
    Args:
        hour (int): The hour (0-23).
        minute (int): The minute (0-59).
    
    Returns:
        str: Time in AM/PM format (e.g., "3:45 pm").
    
    Raises:
        ValueError: If hour or minute values are invalid.
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
    
    Args:
        date_str (str): The date string.
        fmt (str): The expected date format (default: "%Y-%m-%d").
    
    Raises:
        ValueError: If the date format is incorrect.
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

    Args:
        date (str): The date in 'YYYY-MM-DD' format.
        hour (int): The hour in 24-hour format.
        minute (int): The minute (0-59).

    Returns:
        bool: True if the date and time is in the future, False otherwise.
    """
    # Convert input date and time to a datetime object
    input_datetime = datetime.strptime(date, "%Y-%m-%d").replace(hour=hour, minute=minute)

    # Get current date and time
    now = datetime.now()

    # Return True if input date is in the future, False if it's in the past
    return input_datetime > now

def receiving_reservation(driver_local, first_name_local, last_name_local, mobil_number_local, email_local, special_requests_local=None):
    overall_start = time.perf_counter()
    logger.info("Starting reservation process...")

    # Locate form fields
    try:
        firstName = driver_local.find_element(By.XPATH, "//input[contains(@name, 'firstName')]")
        firstName.send_keys(first_name_local)
        firstName.send_keys(Keys.RETURN)
        logger.info("Successfully filled FirstName field.")
    except NoSuchElementException as e:
        msg = f"One or more form fields not found: {e}"
        logger.error(msg)
        return False, msg
    
    try:
        lastName = driver_local.find_element(By.XPATH, "//input[contains(@name, 'lastName')]")
        lastName.send_keys(last_name_local)
        lastName.send_keys(Keys.RETURN)
        logger.info("Successfully filled LastName field.")
    except NoSuchElementException as e:
        msg = f"One or more form fields not found: {e}"
        logger.error(msg)
        return False, msg
    
    try:
        phoneNumber = driver_local.find_element(By.XPATH, "//input[contains(@name, 'phoneNumber')]")
        phoneNumber.send_keys(mobil_number_local)
        phoneNumber.send_keys(Keys.RETURN)
        logger.info("Successfully filled PhoneNumber field.")
    except NoSuchElementException as e:
        msg = f"One or more form fields not found: {e}"
        logger.error(msg)
        return False, msg
    
    try:
        email = driver_local.find_element(By.XPATH, "//input[contains(@name, 'email')]")
        # email.send_keys(email_local)
        email.send_keys({generate_random_email()})
        email.send_keys(Keys.RETURN)
        logger.info("Successfully filled Email field.")
    except NoSuchElementException as e:
        msg = f"One or more form fields not found: {e}"
        logger.error(msg)
        return False, msg
    
    try:
        textUpdatesCheckbox = driver_local.find_element(By.XPATH, "//input[contains(@name, 'optInSmsNotifications')]")
        textUpdatesCheckbox.click()
        logger.info("Checked SMS notifications option.")
    except NoSuchElementException as e:
        msg = f"One or more form fields not found: {e}"
        logger.error(msg)
        return False, msg
    try:
        confirmReservationButton = WebDriverWait(driver_local, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
        )
        confirmReservationButton.click()
        logger.info("Clicked confirm button.")
    except NoSuchElementException:
        msg = "Confirm button not clickable in time."
        logger.error(msg)
        return False, msg
    try:
        timeConformButton = WebDriverWait(driver_local, 3).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@role='link']"))
        )
        timeConformButton.click()
        logger.info("Clicked conform link.")
    except NoSuchElementException:
        msg = "Time conform button not clickable in time."
        logger.error(msg)
        return False, msg
    cancelReservationLinkTag = WebDriverWait(driver_local, 3).until(
        EC.element_to_be_clickable((By.XPATH, "//a[contains(@data-auto, 'cancelReservationLink')]"))
    )
    cancelReservationLink = cancelReservationLinkTag.get_attribute("href")
    logger.info("Captured cancel reservation link successfully.")
    cancel_rid = cancelReservationLink.split("?")[1].split("&")[0].split("=")[1]
    cancel_confnumber = cancelReservationLink.split("?")[1].split("&")[1].split("=")[1]
    cancel_reservationToken = cancelReservationLink.split("?")[1].split("&")[2].split("=")[1]
    cancel_restref          = cancelReservationLink.split("?")[1].split("&")[3].split("=")[1]
    cancel_lang             = cancelReservationLink.split("?")[1].split("&")[4].split("=")[1]
    cancelReservationURL = (
        "https://www.opentable.com/booking/view?showCancelModal=true&rid=" + cancel_rid +
        "&confnumber=" + cancel_confnumber +
        "&token=" + cancel_reservationToken +
        "&restref=" + cancel_restref +
        "&lang=" + cancel_lang
    )

    logger.info("Captured cancel reservation URL successfully. URL: %s", cancelReservationURL)
    modifyReservationLinkTag = WebDriverWait(driver_local, 3).until(
        EC.element_to_be_clickable((By.XPATH, "//a[contains(@data-auto, 'modifyReservationLink')]"))
    )
    modifyReservationLink = modifyReservationLinkTag.get_attribute("href")
    
    logger.info("Captured modify reservation link successfully. URL: %s", modifyReservationLink)
    try:
        start = time.perf_counter()
        modify_rid              = modifyReservationLink.split("?")[1].split("&")[0].split("=")[1]
        modify_confnumber       = modifyReservationLink.split("?")[1].split("&")[1].split("=")[1]
        modify_reservationToken = modifyReservationLink.split("?")[1].split("&")[2].split("=")[1]
        modify_lang = modifyReservationLink.split("?")[1].split("&")[3].split("=")[1]
        modifyReservationURL = (
            "https://www.opentable.com/book/modify?restaurantId=" + modify_rid +
            "&confirmationNumber=" + modify_confnumber +
            "&securityToken=" + modify_reservationToken +
            "&lang=" + modify_lang
        )
        elapsed = time.perf_counter() - start
        logger.info("Captured modify reservation URL in %.4f seconds", elapsed)
        logger.info("Modify reservation URL: %s", modifyReservationURL)
    except Exception as e:
        logger.error("Failed to capture modify reservation URL. Error: %s", e)
        return False, f"Error: {e}"
    confirmation_url = cancelReservationURL
    logger.info("Reservation created successfully. CancelReservation URL: %s", confirmation_url)
    total_elapsed = time.perf_counter() - overall_start
    logger.info("Total time in receiving_reservation: %.4f seconds", total_elapsed)
    return True, confirmation_url

def make_reservation_external(
    date: str = '2025-03-04',
    hour: int = 19,
    minute: int = 0,
    party_size: str = '2',
    first_name: str = 'blabla',
    last_name: str = 'albalb',
    phone_number: str = '+12543252381',
    email: str = 'jato.ft2@gmail.com',
    restaurant_id: str = 'https://www.nomichicago.com/',
    browser_url: str = "",
    proxy_host: str = None,
    proxy_port: int = None,
    proxy_username: str = None,
    proxy_password: str = None,
    proxy_scheme: str = "http",
    make_booking: bool = False,
    special_requests: str = None
):
    overall_start = time.perf_counter()
    driver = None
    try:
        try:
            validate_date(date)
            requested_am_pm = convert_to_am_pm(hour, minute)
        except ValueError as e:
            return (False, None, None, str(e))
        
        if validate_reservation_date(date, hour, minute):
            logger.info("Valid reservation date and time.")
        else:
            logger.error("Invalid reservation: Date and time is in the past.")
            return (False, None, None, "Invalid reservation: Date and time is in the past.")
        
        logger.info(
            "Attempting reservation with details: Date: %s, Time: %02d:%02d (%s), Party Size: %s, First Name: %s, Last Name: %s, Phone: %s, Email: %s, Restaurant ID: %s, Special Requests: %s",
            date, hour, minute, requested_am_pm, party_size, first_name, last_name, phone_number, email, restaurant_id, special_requests
        )
        
        try:
            driver = setup_driver(browser_url, proxy_host, proxy_port, proxy_username, proxy_password, proxy_scheme)
            logger.info("WebDriver initialized successfully.")
        except WebDriverException as e:
            logger.exception("WebDriver initialization failed.")
            return (False, None, None, f"WebDriver error: {e}")
        
        if make_booking:
            try:
                logger.info("Checking reservation availability for booking...")
                reservation_link = restaurant_id
                logger.info("Navigating to reservation link: %s", reservation_link)
                start = time.perf_counter()
                driver.get(reservation_link)
                elapsed = time.perf_counter() - start
                logger.info("Navigation completed in %.4f seconds", elapsed)
                
                logger.info("Redirecting to OpenTable... ")
                start = time.perf_counter()
                element = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'opentable')]"))
                )
                element.click()
                elapsed = time.perf_counter() - start
                logger.info("Redirecting completed in %.4f seconds", elapsed)
        
                driver.switch_to.window(driver.window_handles[-1])
        
                logger.info("Setting up party size... ")
                start = time.perf_counter()
                try:
                    partySizePicker = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.XPATH, "//select[contains(@data-auto, 'partySizePicker')]"))
                    )
                except TimeoutException:
                    logger.error("Party size picker not found within the timeout period.")
                    return (False, None, None, "Party size picker not found.")
                            
                try:
                    select_partySize = Select(partySizePicker)
                    select_partySize.select_by_value(f"{party_size}")
                except Exception as e:
                    logger.error("Error selecting party size: %s", e)
                    return (False, None, None, f"Error selecting party size: {e}")  
             
                elapsed = time.perf_counter() - start
                logger.info("Party size set up in %.4f seconds", elapsed)
                
                
                logger.info("Setting up party date: %s", date)
                start = time.perf_counter()
                try:
                    datePicker = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.XPATH, "//input[contains(@data-auto, 'calendarDatePicker')]"))
                    )
                    datePicker.click()                    
                    calendarHeader = driver.find_element(By.CLASS_NAME, "react-datepicker__current-month")
                    monthName = datetime.strptime(date, "%Y-%m-%d").strftime("%B")
                    while monthName not in calendarHeader.text:
                        nextMonthButton = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Next Month')]")
                        nextMonthButton.click()
                        calendarHeader = driver.find_element(By.CLASS_NAME, "react-datepicker__current-month")
                    
                    day = datetime.strptime(date, "%Y-%m-%d").day
                    ordinal_suffix = get_ordinal_suffix(day)
                    dayButton = driver.find_element(By.XPATH, f"//div[contains(@aria-label, '{monthName} {day}{ordinal_suffix}, {datetime.strptime(date, '%Y-%m-%d').year}')]")
                    dayButton.click()
                
                except TimeoutException:
                    logger.error("Date picker not found within the timeout period.")
                    return (False, None, None, "Date picker not found.")
                
                if minute < 30:
                    requested_time = f"{hour:02d}:00"
                else:
                    requested_time = f"{hour:02d}:30"
                
                logger.info("Setting up party time: %s", requested_time)
                start = time.perf_counter()
                try:
                    timePicker = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.XPATH, "//select[contains(@data-auto, 'timePicker')]"))
                    )
                except TimeoutException:
                    logger.error("Time picker not found within the timeout period.")
                    return (False, None, None, "Time picker not found.")
                            
                try:    
                    select_partyTime = Select(timePicker)
                    available_values = [option.get_attribute("value") for option in select_partyTime.options]
                    option_exists = requested_time in available_values
                    if option_exists:
                        select_partyTime.select_by_value(f"{requested_time}")
                except Exception as e:
                    logger.error("Error selecting party time: %s", e)
                    return (False, None, None, f"Error selecting party time: {e}")
                
                elapsed = time.perf_counter() - start
                logger.info("Party time set up in %.4f seconds", elapsed)
                
                logger.info("Locating availability button... ")
                start = time.perf_counter()
                findingTable_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
                )
                findingTable_button.click()
                elapsed = time.perf_counter() - start
                logger.info("Clicked finding table button in %.4f seconds", elapsed)
                
                try:
                    availabilityButtons = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.XPATH, "//button[contains(@role, 'link')]"))
                    )
                    logger.info("Found %d availability buttons.", len(availabilityButtons))
                except TimeoutException:
                    logger.error("Availability buttons not found within the wait period.")
                    return (False, None, None, "Availability buttons not found.")
                
                exact_slot = None
                nearestTime = 0
                isEmptyTimeButton = True
                
                for button in availabilityButtons:  
                    if button.text != "":
                        nearestTime = time_difference_in_minutes(requested_am_pm, button.text)
                        isEmptyTimeButton = False
                        exact_slot = button
                        break
        
                logger.info("Total availability buttons found: %d", len(availabilityButtons))
        
                for button in availabilityButtons:  
                    if button.text == requested_am_pm:
                        exact_slot = button
                        isEmptyTimeButton = False
                        break
                    elif button.text != "" and "tify" not in button.text:
                        minutes = time_difference_in_minutes(requested_am_pm, button.text)
                        logger.info("Button text: %s, diff minutes: %d, current nearest: %d", button.text, minutes, nearestTime)
                        if nearestTime > minutes:
                            nearestTime = minutes
                            exact_slot = button
                            isEmptyTimeButton = False
                            logger.info("New nearest time: %s", button.text)
                        
                if isEmptyTimeButton or exact_slot is None:
                    return (False, None, None, "No availability available")
            
                logger.info("Selected availability: %s", exact_slot.text)
                exact_slot.click()
                
                reservationSelectButton = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[text()='Select']"))
                )
                reservationSelectButton.click()
                
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//input[contains(@name, 'firstName')]"))
                )
            
                error_msg = ""
                try:
                    booking_result, booking_info = receiving_reservation(driver, first_name, last_name, phone_number, email)
                    if booking_result:
                        booked = True
                        confirmation_url = booking_info
                        logger.info("Booking successful. CancelReservation URL: %s", confirmation_url)
                    else:
                        error_msg = booking_info
                        logger.error("Booking failed: %s", error_msg)
                except Exception as e:
                    logger.exception("Unexpected error during reservation process")
                    return (False, None, None, f"Unexpected error: {e}")
            
                total_elapsed = time.perf_counter() - overall_start
                logger.info("Total booking process time: %.4f seconds", total_elapsed)
                return (booked, confirmation_url if booked else None, None, error_msg)
            except Exception as e:
                logger.exception("Unexpected error during booking process")
                return (False, None, None, f"Unexpected error: {e}")
        else:
            try:
                logger.info("Checking reservation availability (no booking attempt)...")
                reservation_link = restaurant_id
                logger.info("Navigating to reservation link: %s", reservation_link)
                start = time.perf_counter()
                driver.get(reservation_link)
                elapsed = time.perf_counter() - start
                logger.info("Navigation completed in %.4f seconds", elapsed)
                
                logger.info("Redirecting to OpenTable... ")
                start = time.perf_counter()
                element = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'opentable')]"))
                )
                element.click()
                elapsed = time.perf_counter() - start
                logger.info("Redirecting completed in %.4f seconds", elapsed)
        
                driver.switch_to.window(driver.window_handles[-1])
        
                logger.info("Setting up party size... ")
                start = time.perf_counter()
                try:
                    partySizePicker = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.XPATH, "//select[contains(@data-auto, 'partySizePicker')]"))
                    )
                except TimeoutException:
                    logger.error("Party size picker not found within the timeout period.")
                    return (False, None, None, "Party size picker not found.")
                            
                try:
                    select_partySize = Select(partySizePicker)
                    select_partySize.select_by_value(f"{party_size}")
                except Exception as e:
                    logger.error("Error selecting party size: %s", e)
                    return (False, None, None, f"Error selecting party size: {e}")
             
                elapsed = time.perf_counter() - start
                logger.info("Party size set up in %.4f seconds", elapsed)
        
                if minute < 30:
                    requested_time = f"{hour:02d}:00"
                else:
                    requested_time = f"{hour:02d}:30"
                
                logger.info("Setting up party time: %s", requested_time)
                start = time.perf_counter()
                try:
                    timePicker = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.XPATH, "//select[contains(@data-auto, 'timePicker')]"))
                    )
                except TimeoutException:
                    logger.error("Time picker not found within the timeout period.")
                    return (False, None, None, "Time picker not found.")
                            
                try:    
                    select_partyTime = Select(timePicker)
                    option_exists = any(option.get_attribute("value") == requested_time for option in select_partyTime.options)
                    if option_exists:
                        select_partyTime.select_by_value(f"{requested_time}")
                except Exception as e:
                    logger.error("Error selecting party time: %s", e)
                    return (False, None, None, f"Error selecting party time: {e}")
                
                elapsed = time.perf_counter() - start
                logger.info("Party time set up in %.4f seconds", elapsed)
                
                logger.info("Locating availability button... ")
                start = time.perf_counter()
                findingTable_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
                )
                findingTable_button.click()
                elapsed = time.perf_counter() - start
                logger.info("Clicked finding table button in %.4f seconds", elapsed)
                
                try:
                    availabilityButtons = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.XPATH, "//button[contains(@role, 'link')]"))
                    )
                    logger.info("Found %d availability buttons.", len(availabilityButtons))
                except TimeoutException:
                    logger.error("Availability buttons not found within the wait period.")
                    return (False, None, None, "Availability buttons not found.")
                
                exact_slot = None
                nearestTime = 0
                isEmptyTimeButton = True
                
                for button in availabilityButtons:  
                    if button.text != "":
                        nearestTime = time_difference_in_minutes(requested_am_pm, button.text)
                        isEmptyTimeButton = False
                        exact_slot = button
                        break
        
                logger.info("Total availability buttons found: %d", len(availabilityButtons))
        
                for button in availabilityButtons:  
                    if button.text == requested_am_pm:
                        exact_slot = button
                        isEmptyTimeButton = False
                        break
                    elif button.text != "" and "tify" not in button.text:
                        minutes = time_difference_in_minutes(requested_am_pm, button.text)
                        if nearestTime > minutes:
                            nearestTime = minutes
                            exact_slot = button
                            isEmptyTimeButton = False
                            
                if isEmptyTimeButton or exact_slot is None:
                    return (False, None, None, "No availability available")
                
                alternativeTime = exact_slot.text
                logger.info("Nearest availability: %s", alternativeTime)
                
                if alternativeTime != requested_am_pm:
                    alt_times_str = f"Alternative times available: {alternativeTime}"
                    logger.info(alt_times_str)
                else:
                    logger.info("Exact time available but booking not attempted (make_booking is False).")
                    
                total_elapsed = time.perf_counter() - overall_start
                logger.info("Total process time: %.4f seconds", total_elapsed)
                return (True, None, None, None)
            except Exception as e:
                logger.exception("Unexpected error during availability checking process:")
                return (False, None, None, f"Unexpected error: {e}")
    finally:
        if driver is not None:
            driver.quit()
            logger.info("WebDriver session closed.")
            
def cancel_reservation(cancel_url: str = ""):
    overall_start = time.perf_counter()
    logger.info("Starting cancelling process...")
    try:
        driver = webdriver.Chrome()
        driver.set_window_size(1300, 1070)
        logger.info("WebDriver initialized successfully.")
    except WebDriverException as e:
        logger.exception("WebDriver initialization failed.")
        return (False, f"WebDriver error: {e}")
    logger.info("Navigating to cancelling URL: %s", cancel_url)
    start = time.perf_counter()
    try:
        driver.get(cancel_url)
    except WebDriverException as e:
        logger.exception("Navigation to cancelling URL failed: %s", cancel_url)
        return (False, f"WebDriver error: {e}")
    elapsed = time.perf_counter() - start
    logger.info("Cancel page loaded in %.4f seconds", elapsed)
    try:
        cancel_button = driver.find_element(By.XPATH, "//button[@data-test='continue-cancel-button']")
        elapsed = time.perf_counter() - start
        logger.info("Cancel button became visible in %.4f seconds", elapsed)
        cancel_button.click()
        logger.info("Clicked the cancel button")
    except TimeoutException:
        elapsed = time.perf_counter() - overall_start
        logger.error("Cancel button did not appear after %.4f seconds", elapsed)
        return (False, "Cancel button did not appear.")
    except Exception as e:
        logger.exception("Unexpected error while cancelling: %s", str(e))
        return (False, f"Unexpected error: {str(e)}")
    try:
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'has canceled your reservation')]"))
        )
        elapsed = time.perf_counter() - start
        logger.info("Cancel reservation message visible in %.4f seconds", elapsed)
        return (True, "The requested reservation is cancelled")
    except TimeoutException:
        elapsed = time.perf_counter() - overall_start
        logger.error("Cancel reservation message did not appear after %.4f seconds", elapsed)
        return (False, "Cancel reservation message did not appear.")
    except Exception as e:
        logger.exception("Unexpected error while waiting for cancellation confirmation: %s", str(e))
        return (False, f"Unexpected error: {str(e)}")

if __name__ == '__main__':
    
    # Oxylabs Proxy Configuration (masked for security)
    OX_PROXY_HOST = "pr.oxylabs.io"         # Use the Oxylabs proxy host as given.
    OX_PROXY_PORT = 7777                    # Use port 7777 as in the endpoint examples.
    OX_PROXY_USERNAME = "customer-dined_uDNrH-cc-us"  # Make sure there are no extra spaces.
    OX_PROXY_PASSWORD = "dPx_________1"     # Your proxy password.
    
    # Optionally, set proxy_scheme to "http" or "socks5h" if needed.
    PROXY_SCHEME = "http"                   # or "socks5h"

    # Oxylabs Proxy Configuration (masked for security)
    BROWSER_URL = ""
    RESTAURANT_ID = "https://www.nomichicago.com/"

    result = make_reservation_external(
        date="2025-03-23",
        hour=12,
        minute=30,
        party_size="4",
        first_name="bvvdlabsdlasd",
        last_name="alsdbavsdlb",
        email="tesht2137j56476@dinedaiserver.online",
        phone_number="19392227739",
        special_requests="Window seat preferred",
        make_booking=True,  # Set to True to attempt booking.
        restaurant_id=RESTAURANT_ID,
        browser_url=BROWSER_URL,
        proxy_host=OX_PROXY_HOST,
        proxy_port=OX_PROXY_PORT,
        proxy_username=OX_PROXY_USERNAME,
        proxy_password=OX_PROXY_PASSWORD,
        proxy_scheme=PROXY_SCHEME
    )
    logger.info("Result: %s", result)

    # result = cancel_reservation(
    #     cancel_url= "https://www.opentable.com/booking/view?showCancelModal=true&rid=1479&confnumber=2110753617&token=01ZT_UO-xcbPxHy1sreNsuJqw_c5u5VvMCV-YZH0hGc9M1&restref=1479&lang=en-US"
    # )
    # logger.info("Result: %s", result)
