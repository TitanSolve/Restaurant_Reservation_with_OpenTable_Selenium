import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, InvalidElementStateException
from selenium.webdriver.common.keys import Keys
from config import logger
from utils import (
    find_element_with_timing,
    find_elements_with_timing,
    convert_to_am_pm,
    validate_date,
    validate_reservation_date
)
from driver import setup_driver

def receiving_reservation(driver_local, first_name_local, last_name_local, mobil_number_local, email_local, special_requests_local=None):
    overall_start = time.perf_counter()
    logger.info("Starting reservation process...")

    try:
        start = time.perf_counter()
        WebDriverWait(driver_local, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//h5[contains(text(), 'Your Information')]"))
        )
        elapsed = time.perf_counter() - start
        logger.info("Reservation form loaded in %.4f seconds", elapsed)
    except TimeoutException:
        msg = "Reservation form did not load in time."
        logger.error(msg)
        return False, msg

    try:
        first_name_box = find_element_with_timing(driver_local, By.XPATH, "//label[.//span[contains(text(),'First Name')]]//input", "First Name field")
        last_name_box = find_element_with_timing(driver_local, By.XPATH, "//label[.//span[contains(text(),'Last Name')]]//input", "Last Name field")
        mobile_number_box = find_element_with_timing(driver_local, By.XPATH, "//label[.//span[contains(text(),'Mobile Number')]]//input", "Mobile Number field")
        email_box = find_element_with_timing(driver_local, By.XPATH, "//label[.//span[contains(text(),'Email')]]//input", "Email field")
    except NoSuchElementException as e:
        msg = f"One or more form fields not found: {e}"
        logger.error(msg)
        return False, msg

    fields = {
        "first_name": (first_name_box, first_name_local),
        "last_name": (last_name_box, last_name_local),
        "mobile_number": (mobile_number_box, mobil_number_local),
        "email": (email_box, email_local)
    }

    validation_errors = []
    for field_name, (input_box, value) in fields.items():
        try:
            input_box.clear()
            input_box.send_keys(value)
            logger.info("Successfully filled %s field.", field_name)
        except InvalidElementStateException:
            logger.error("Field '%s' is in an invalid state and cannot be filled.", field_name)
            validation_errors.append(f"{field_name} field cannot be modified.")
        except Exception as e:
            logger.error("Unexpected error while filling '%s': %s", field_name, e)
            validation_errors.append(f"Unexpected error in {field_name}: {str(e)}")

    email_box.send_keys(Keys.TAB)

    error_messages = {
        "maximum_input": "//span[contains(text(), 'you exceeded the maximum number of characters')]",
        "name_invalid_characters": "//span[contains(text(), 'Field contains invalid characters')]",
        "mobile_number": "//span[contains(text(), 'valid phone number')]",
        "email": "//span[contains(text(), 'valid email')]"
    }

    for field, error_xpath in error_messages.items():
        try:
            error_elements = WebDriverWait(driver_local, 1).until(
                EC.presence_of_all_elements_located((By.XPATH, error_xpath))
            )
            for error_element in error_elements:
                error_text = error_element.text.strip()
                logger.error("Validation error for %s: %s", field, error_text)
                validation_errors.append(f"{field}: {error_text}")
        except TimeoutException:
            pass
        except Exception as e:
            logger.error("Unexpected error while checking validation for %s: %s", field, e)

    if validation_errors:
        logger.error("Form validation failed with errors: %s", validation_errors)
        return False, "Form validation errors: " + ", ".join(validation_errors)

    if special_requests_local:
        try:
            special_requests_box = find_element_with_timing(driver_local, By.XPATH, "//label[.//span[contains(text(),'Requests')]]//input", "Special Requests field")
            special_requests_box.send_keys(special_requests_local)
        except NoSuchElementException:
            logger.warning("Special requests field not found; skipping.")

    try:
        start = time.perf_counter()
        confirm_box = WebDriverWait(driver_local, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@data-button='true' and .//span[normalize-space()='Confirm']]"))
        )
        elapsed = time.perf_counter() - start
        logger.info("Confirm button found in %.4f seconds", elapsed)
        confirm_box.click()
    except TimeoutException:
        msg = "Confirm button not clickable in time."
        logger.error(msg)
        return False, msg

    CANCEL_BUTTON_LOCATOR = (By.XPATH, "//button[@data-button='true' and .//span[normalize-space()='Cancel']]")
    ERROR_MESSAGE_LOCATOR = (By.XPATH, "//div[@aria-label='Error' and @role='alert']")

    try:
        start = time.perf_counter()
        WebDriverWait(driver_local, 10).until(
            EC.any_of(
                EC.presence_of_element_located(CANCEL_BUTTON_LOCATOR),
                EC.presence_of_element_located(ERROR_MESSAGE_LOCATOR)
            )
        )
        elapsed = time.perf_counter() - start
        logger.info("Detected confirmation elements (Cancel button or Error) in %.4f seconds", elapsed)
    except TimeoutException:
        msg = "Timed out waiting for confirmation or error indicator."
        logger.error(msg)
        return False, msg

    if driver_local.find_elements(*CANCEL_BUTTON_LOCATOR):
        confirmation_url = driver_local.current_url
        logger.info("Reservation created successfully. Confirmation URL: %s", confirmation_url)
        total_elapsed = time.perf_counter() - overall_start
        logger.info("Total time in receiving_reservation: %.4f seconds", total_elapsed)
        return True, confirmation_url
    else:
        try:
            error_text = driver_local.find_element(*ERROR_MESSAGE_LOCATOR).text
        except NoSuchElementException:
            error_text = "Unknown error occurred."
        logger.error("Error creating reservation: %s", error_text)
        total_elapsed = time.perf_counter() - overall_start
        logger.info("Total time in receiving_reservation: %.4f seconds", total_elapsed)
        return False, error_text

def make_reservation(
    date: str = '2025-02-14',
    hour: int = 19,
    minute: int = 0,
    party_size: str = '2',
    first_name: str = 'blabla',
    last_name: str = 'albalb',
    phone_number: str = '+12543252381',
    email: str = 'reservation@dinedaiserver.online',
    restaurant_id: str = 'mikiya-wagyu-shabu-house-new-york-3',
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
    booked = False
    confirmation_url = None
    alt_times_str = None
    error_msg = None

    try:
        validate_date(date)
        requested_am_pm = convert_to_am_pm(hour, minute)
    except ValueError as e:
        return (False, None, None, str(e))
    
    requested_24 = f"{hour:02d}{minute:02d}"
    
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
    except Exception as e:
        logger.exception("WebDriver initialization failed.")
        return (False, None, None, f"WebDriver error: {e}")
    
    try:
        if make_booking:
            checkout_url = f"https://www.yelp.com/reservations/{restaurant_id}/checkout/{date}/{requested_24}/{party_size}"
            logger.info("Starting booking process. Navigating to checkout URL: %s", checkout_url)
        
            start = time.perf_counter()
            try:
                driver.get(checkout_url)
            except Exception as e:
                logger.exception("WebDriver failed to navigate to checkout URL: %s", checkout_url)
                return (False, None, None, f"WebDriver error: {e}")
        
            elapsed = time.perf_counter() - start
            logger.info("Checkout page loaded in %.4f seconds", elapsed)
        
            try:
                WebDriverWait(driver, 15).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.XPATH, "//div[@aria-label='Error' and @role='alert']")),
                        EC.presence_of_element_located((By.XPATH, "//h2[contains(text(),'Confirm Reservation')]"))
                    )
                )
            except TimeoutException:
                elapsed = time.perf_counter() - overall_start
                logger.error("Checkout page did not load properly after %.4f seconds", elapsed)
                return (False, None, None, "Checkout page did not load properly.")
        
            error_elements = driver.find_elements(By.XPATH, "//div[@aria-label='Error' and @role='alert']")
            if error_elements:
                error_text = error_elements[0].text.strip()
                logger.error("Checkout error detected: %s", error_text)
                return (False, None, None, error_text)
        
            logger.info("No errors found on checkout page. Proceeding with reservation.")
        
            try:
                booking_result, booking_info = receiving_reservation(driver, first_name, last_name, phone_number, email, special_requests)
                if booking_result:
                    booked = True
                    confirmation_url = booking_info
                    logger.info("Booking successful. Confirmation URL: %s", confirmation_url)
                else:
                    error_msg = booking_info
                    logger.error("Booking failed: %s", error_msg)
            except Exception as e:
                logger.exception("Unexpected error during reservation process")
                return (False, None, None, f"Unexpected error: {e}")
        
            total_elapsed = time.perf_counter() - overall_start
            logger.info("Total booking process time: %.4f seconds", total_elapsed)
        
            return (booked, confirmation_url if booked else None, None, error_msg)

        else:
            logger.info("Checking reservation availability... ")
            reservation_link = f"https://www.yelp.com/reservations/{restaurant_id}?date={date}&time={requested_24}&covers={party_size}"
            logger.info("Navigating to reservation link: %s", reservation_link)
        
            start = time.perf_counter()
            driver.get(reservation_link)
            elapsed = time.perf_counter() - start
            logger.info("Navigation completed in %.4f seconds", elapsed)

            try:
                date_obj = datetime.strptime(date, "%Y-%m-%d")
                formatted_date_win = date_obj.strftime("%b ") + str(date_obj.day)
                input_xpath = "//input[@aria-label='Select a date']"
                element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, input_xpath))
                )
                value = element.get_attribute("value")
                if formatted_date_win in value:
                    logger.info(f"Reservation date {formatted_date_win} is in allowed range.")
                else:
                    logger.error(f"Reservation date {formatted_date_win} is not in allowed range.")
                    return (False, None, None, f"Reservation date {formatted_date_win} is not in allowed range.")
        
            except TimeoutException:
                logger.error("Timeout: Date input field was not found within the given time.")
                return (False, None, None, "Timeout: Date input field was not found within the given time.")
            except NoSuchElementException:
                logger.error("Date input field does not exist on the page.")
                return (False, None, None, "Date input field does not exist on the page.")
            except Exception as e:
                return (False, None, None, f"Unexpected error: {str(e)}")

            try:
                time.sleep(2) # Fix fixed sleep
                if int(party_size) > 1:
                    option = driver.find_element(By.XPATH, f"//option[text()='{party_size} people']")
                elif int(party_size) == 1:
                    option = driver.find_element(By.XPATH, f"//option[text()='1 person']")
                else:
                    logger.error("Party size is invalid.")
                    return (False, None, None, "Party size is not in allowed range.")
                logger.info(f"The party size {party_size} is in allowed range.")
            except TimeoutException:
                logger.error(f"The party size {party_size} is bigger than maximum.")
                return (False, None, None, "The party size is bigger than maximum.")
            except NoSuchElementException:
                logger.error(f"The party size {party_size} is bigger than maximum.")
                return (False, None, None, "The party size is bigger than maximum.")
            except Exception as e:
                logger.exception("Unexpected error while checking the party size")
                return (False, None, None, f"Unexpected error: {str(e)}")
            
            xpath = ("//button[@data-button='true' and not(.//span[normalize-space()='Confirm']) and "
                     "(.//span[contains(text(),'am')] or .//span[contains(text(),'pm')])]")
        
            start = time.perf_counter()
            try:
                WebDriverWait(driver, 10).until(
                    EC.any_of(
                        EC.visibility_of_element_located((By.XPATH, xpath)),
                        EC.presence_of_element_located((By.XPATH, "//p[text()='No Availability']"))
                    )
                )
                elapsed = time.perf_counter() - start
                logger.info("Time slot elements became visible in %.4f seconds", elapsed)
            except TimeoutException:
                logger.error("Time slot elements did not appear after %.4f seconds", time.perf_counter() - overall_start)
                return (False, None, None, "Time slot elements did not appear.")
            except NoSuchElementException:
                logger.info("Time slot elements could not be found on the page.")
                return (False, None, None, "Sorry, that spot is no longer available. Feel free to check back later, or search for a different date.")
            except Exception as e:
                logger.exception("Unexpected error while waiting for time slot elements: %s", str(e))
                return (False, None, None, f"Unexpected error: {str(e)}")
        
            time_slot_buttons = find_elements_with_timing(driver, By.XPATH, xpath, "time slot button")
            if not time_slot_buttons:
                logger.error("No time slot buttons found on the page.")
                return (False, None, None, "No time slot buttons found on the page.")
        
            requested_dt = datetime.strptime(requested_am_pm, "%I:%M %p")
            base_index = 3
        
            if base_index < len(time_slot_buttons):
                base_time_text = driver.execute_script("return arguments[0].innerText;", time_slot_buttons[base_index]).strip()
                try:
                    base_time = datetime.strptime(base_time_text, "%I:%M %p")
                except ValueError as e:
                    logger.warning("Could not parse base time text '%s': %s", base_time_text, e)
                    base_time = None
            else:
                base_time = None
        
            order = [3, 2, 4, 1, 5, 0, 6] if base_time and base_time > requested_dt else [3, 4, 2, 5, 1, 6, 0]
            order = [i for i in order if i < len(time_slot_buttons)]
        
            exact_slot = None
            candidate_left = None
            candidate_right = None
        
            for idx in order:
                button = time_slot_buttons[idx]
                start = time.perf_counter()
                time_text = driver.execute_script("return arguments[0].innerText;", button).strip()
                extraction_time = time.perf_counter() - start
                logger.info("Extracted time_text '%s' from button %d in %.4f seconds", time_text, idx+1, extraction_time)
        
                try:
                    slot_time = datetime.strptime(time_text, "%I:%M %p")
                except ValueError as e:
                    logger.warning("Could not parse time_text '%s' from button %d: %s", time_text, idx+1, e)
                    continue
        
                available = button.get_attribute("disabled") is None
                logger.info("Button %d: time_text='%s', available=%s", idx+1, time_text, available)
        
                if not available:
                    continue
        
                if slot_time == requested_dt:
                    exact_slot = button
                    logger.info("Exact requested time (%s) found at button %d and available.", requested_am_pm, idx+1)
                    break
                elif slot_time < requested_dt and candidate_left is None:
                    candidate_left = (time_text, button, slot_time)
                    logger.info("Found left alternative: %s at button %d", time_text, idx+1)
                elif slot_time > requested_dt and candidate_right is None:
                    candidate_right = (time_text, button, slot_time)
                    logger.info("Found right alternative: %s at button %d", time_text, idx+1)
        
                if candidate_left and candidate_right:
                    break
        
            if exact_slot:
                if make_booking:
                    start = time.perf_counter()
                    exact_slot.click()
                    click_elapsed = time.perf_counter() - start
                    logger.info("Clicked exact time button in %.4f seconds", click_elapsed)
        
                    booking_result, booking_info = receiving_reservation(driver, first_name, last_name, phone_number, email, special_requests)
                    if booking_result:
                        logger.info("Booking successful. Confirmation URL: %s", booking_info)
                        booked = True
                        confirmation_url = booking_info
                    else:
                        logger.error("Booking failed: %s", booking_info)
                        error_msg = booking_info
        
                    total_elapsed = time.perf_counter() - overall_start
                    logger.info("Total booking time: %.4f seconds", total_elapsed)
                    return (booked, confirmation_url if booked else None, None, error_msg)
                else:
                    logger.info("Exact time available but booking not attempted (make_booking is False).")
                    return (True, None, None, None)
            else:
                alternatives = []
                if candidate_left:
                    alternatives.append(candidate_left[0].upper().replace(":00", ""))
                if candidate_right:
                    alternatives.append(candidate_right[0].upper().replace(":00", ""))
                alt_times_str = " or ".join(alternatives) if alternatives else "No alternative times available"
                logger.info("Alternative times: %s", alt_times_str)
        
                total_elapsed = time.perf_counter() - overall_start
                logger.info("Total process time: %.4f seconds", total_elapsed)
                return (False, None, alt_times_str, None)
            
    except KeyboardInterrupt:
        raise
    except Exception as e:
        logger.exception("Unexpected error during reservation process:")
        return (False, None, None, f"Unexpected error: {e}")
    finally:
        if driver is not None:
            driver.quit()
            logger.info("WebDriver session closed.")
