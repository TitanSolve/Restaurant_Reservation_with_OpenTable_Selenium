from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from datetime import datetime
import string
import random
import time

def get_formatted_date():
    today = datetime.today()
    day = today.day
    if 4 <= day <= 20 or 24 <= day <= 30:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}[day % 10]

    formatted_date = today.strftime(f"%B {day}{suffix}, %Y")
    return formatted_date

def time_difference_in_minutes(time1, time2):
    fmt = "%I:%M %p"
    t1 = datetime.strptime(time1, fmt)
    t2 = datetime.strptime(time2, fmt)

    diff = abs((t2 - t1).total_seconds()) // 60
    return int(diff)

def generate_random_email():
    domains = ["gmail.com", "yahoo.com", "outlook.com", "example.com"]
    
    username_length = random.randint(8, 12)
    username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=username_length))

    domain = random.choice(domains)    
    return f"{username}@{domain}"


driver_path = r'E:\chromedriver-win64\chromedriver.exe'
chrome_options = Options()
service = Service(driver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)
wait = WebDriverWait(driver, 10)
driver.set_window_size(1300, 1070)

driver.get("https://www.opentable.com/booking/view?showCancelModal=true&rid=1479&confnumber=2110753606&token=011blr30jPr4e9MqhbMC0ZzQGdv7-jD3CRslfxl3Ew5VU1&restref=1479&lang=en-US")

try:
    reservation_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'opentable')]")))
    reservation_button.click()
    
    time.sleep(5)
    driver.switch_to.window(driver.window_handles[-1])

    print("Redirect OpenTable page success.")

    partySizePicker = driver.find_element(By.XPATH, "//select[contains(@data-auto, 'partySizePicker')]")
    select = Select(partySizePicker)
    select.select_by_value("3")
    
    customDate = "10:30 pm"
        
    time_picker = driver.find_element(By.XPATH, "//select[contains(@data-auto, 'timePicker')]")
    timeSelect = Select(time_picker)
    timeSelect.select_by_value("22:30")
            
    submit_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
    submit_button.click()
    time.sleep(2)
    
    buttons = driver.find_elements(By.CLASS_NAME, "styled__ButtonListItem-sc-1q1dpdt-2")
    nearestTimeButton = None
    nearestTime = 0
    isEmptyTimeButton = True
    
    if len(buttons) > 0:
        nearestTime = time_difference_in_minutes(customDate, buttons[0].text)
    
    for button in buttons:  
        if button.text == customDate:
            nearestTimeButton = button
            isEmptyTimeButton = False
            break
        elif button.text != customDate and button.text != "":
            minutes = time_difference_in_minutes(customDate, button.text)
            print(f"button.text={button.text}, minutes={minutes},nearestTime={nearestTime}")
            if  nearestTime > minutes:
                nearestTime = minutes
                nearestTimeButton = button
                isEmptyTimeButton = False
                print(f"nearestTime={button.text}")
            
    if isEmptyTimeButton:
        print("======================= No time available ==================================")
        time.sleep(2000)
        driver.quit()
    
    print(f"nearest button ={nearestTimeButton.text}")
    nearestTimeButton.click()
        
    time.sleep(3)
    
    reservationSelectButton = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[text()='Select']")))
    reservationSelectButton.click()
    
    # set details
    time.sleep(3)
    firstName = driver.find_element(By.XPATH, "//input[contains(@name, 'firstName')]")
    firstName.send_keys("firstName")
    firstName.send_keys(Keys.RETURN)
    
    lastName = driver.find_element(By.XPATH, "//input[contains(@name, 'lastName')]")
    lastName.send_keys("lastName")
    lastName.send_keys(Keys.RETURN)
    
    phoneNumberCountryPicker = driver.find_element(By.XPATH, "//select[contains(@name, 'phoneNumberCountryId')]")
    phoneNumberCountrySelect = Select(phoneNumberCountryPicker)
    phoneNumberCountrySelect.select_by_value("US")
    
    phoneNumber = driver.find_element(By.XPATH, "//input[contains(@name, 'phoneNumber')]")
    phoneNumber.send_keys("12345678901")
    phoneNumber.send_keys(Keys.RETURN)
    
    
    email = driver.find_element(By.XPATH, "//input[contains(@name, 'email')]")
    email.send_keys({generate_random_email()})
    email.send_keys(Keys.RETURN)
    
    textUpdatesCheckbox = driver.find_element(By.XPATH, "//input[contains(@name, 'optInSmsNotifications')]")
    textUpdatesCheckbox.click()
    time.sleep(3)


    confirmReservationButton = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
    confirmReservationButton.click()
    time.sleep(3)
    
    # Find the button using XPath by matching exact text
    timeConformButton = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@role='link']")))
    timeConformButton.click()
    
    cancelReservationLinkTag = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@data-auto, 'cancelReservationLink')]")))
    cancelReservationLink = cancelReservationLinkTag.get_attribute("href")
    print(f"reservationLink={cancelReservationLink}")
    
    cancel_rid = cancelReservationLink.split("?")[1].split("&")[0].split("=")[1]
    cancel_confnumber = cancelReservationLink.split("?")[1].split("&")[1].split("=")[1]
    cancel_reservationToken = cancelReservationLink.split("?")[1].split("&")[2].split("=")[1]
    cancel_restref = cancelReservationLink.split("?")[1].split("&")[3].split("=")[1]
    cancel_lang = cancelReservationLink.split("?")[1].split("&")[4].split("=")[1]
    cancelReservationURL = "https://www.opentable.com/booking/view?showCancelModal=true&rid=" + cancel_rid + "&confnumber=" + cancel_confnumber + "&token=" + cancel_reservationToken + "&restref=" + cancel_restref + "&lang=" + cancel_lang
    print(f"cancelReservationURL={cancelReservationURL}")
    
    modifyReservationLinkTag = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@data-auto, 'modifyReservationLink')]")))
    modifyReservationLink = modifyReservationLinkTag.get_attribute("href")
    print(f"modifyReservationLink={modifyReservationLink}")
    
    modify_rid = modifyReservationLink.split("?")[1].split("&")[0].split("=")[1]
    modify_confnumber = modifyReservationLink.split("?")[1].split("&")[1].split("=")[1]
    modify_reservationToken = modifyReservationLink.split("?")[1].split("&")[2].split("=")[1]
    modify_lang = modifyReservationLink.split("?")[1].split("&")[4].split("=")[1]
    modifyReservationURL = "https://www.opentable.com/book/modify?restaurantId=" + modify_rid + "&confirmationNumber=" + modify_confnumber + "&securityToken=" + modify_reservationToken + "&restref=" + modify_restref + "&lang=" + modify_lang
    print(f"modifyReservationURL={modifyReservationURL}")


    time.sleep(100)
    
    print("Reservation request submitted successfully!")

except Exception as e:
    print("Error occurred:", e)

# Close browser after some delay
time.sleep(5)
driver.quit()
