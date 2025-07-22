import pandas as pd
import random
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException
from langchain.tools import tool
from playtomic_reservation_utils import (playtomic_schedule,
                            login_playtomic,
                            setup_driver,
                            click_on_select_hour,
                            click_select_and_choose,
                            check_is_correct_schedule_date,
                            check_reservation_exists,
                            check_is_within_schedule,
                            check_is_valid_date
                            )

@tool
def get_playtomic_schedule() -> str:
    """
    Retrieves the schedule of upcoming Playtomc reservations.
    
    Returns:
        str: A Markdown-formatted table of active (non-cancelled) bookings.
    """
    
    schedule = playtomic_schedule()
    
    if isinstance(schedule,str):
        return schedule
    elif isinstance(schedule,pd.DataFrame):
        return "Reservas activas:\n" + schedule.astype(str).to_markdown(index=False)
        
@tool   
def add_playtomic_schedule(day_reservation: str, 
                           fecha_inicio: str, 
                           fecha_fin: str,
                           person_name: str) -> str:
    
    """
    Adds a new reservation to the Playtomic schedule for specific time slot.
    
    This tool logs into Playtomic, navigates to the specified date, selects the
    start and end times and sets the person reservation name.
    It checks for existing overlapping reservations before attempting to create a new one.
    
    Args:
        day_reservation (str): The specific date for the reservation in 'DD-MM-YYYY' format. Example '21-07-2025'
        fecha_inicio (str): The start time of the reservation in 'HH:MM:' format. Example: '10:00'
        fecha_fin (str): The end time of the reservation in 'HH:MM:' format. Example: '11:00'
        person_name (str): The exact name of the person to be reserved. Example: 'Alejandro'

    Returns:
        str: A message indicating the succes or failure of the reservation attempt.
    """
    
    driver = None
        
    schedule = playtomic_schedule()
    
    day_reservation_datetime = datetime.strptime(day_reservation,'%d-%m-%Y')
    
    court_price = '0.0'
        
    try: 
        
        time.sleep(5)
        
        driver = setup_driver()
        wait = WebDriverWait(driver, 20)
        actions = ActionChains(driver)
        
        is_within_schedule = check_is_within_schedule(fecha_inicio, fecha_fin)
        
        if not is_within_schedule:
            return f'Las reservas deben ser entre las 08:30 y las 22:00'
        
        is_valid_date = check_is_valid_date(day_reservation, fecha_inicio)
        
        if not is_valid_date:
            return f'Las reservas deben ser entre hoy y los proximos 14 días'
        
        if isinstance(schedule,str):
            return schedule
        elif isinstance(schedule,pd.DataFrame):
            is_any_match = check_reservation_exists(schedule, day_reservation_datetime, fecha_inicio, fecha_fin)
            if is_any_match:
                return f"La franja para el dia {day_reservation} de {fecha_inicio} a {fecha_fin} ya está ocupada."
        
        login_playtomic(driver,wait)
        
        time.sleep(random.uniform(5,10))
        
        check_is_correct_schedule_date(driver,wait,day_reservation_datetime)

        wait.until(EC.presence_of_element_located((By.XPATH, f"//tr[@data-time='{fecha_inicio}:00']")))
        
        click_on_select_hour(driver,actions,fecha_inicio)
        
        time.sleep(random.uniform(3,5))

        click_select_and_choose(wait,actions,"#startDate div.select__control", fecha_inicio)
        click_select_and_choose(wait,actions,"#endDate div.select__control", fecha_fin)

        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[span[text()='Editar']]"))).click()

        price_input = wait.until(EC.element_to_be_clickable((By.ID, "input-input-1")))
        price_input.clear()
        price_input.send_keys(float(court_price))
        
        time.sleep(random.uniform(3,5))

        input_field = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "input[id^='react-select'][id$='-input']")
        ))

        input_field.send_keys(person_name)

        option = wait.until(EC.element_to_be_clickable(
            (By.XPATH, f"//li//div[@class='ListItemContentstyles__CenterGroup-ny9mc5-2 iTqicv' and contains(., '{person_name}')]")
        ))
        option.click()
        
        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[span[text()='Crear']]"))).click()
        
        time.sleep(5)
        
        return f'Se ha añadido la reserva al calendario para el dia {day_reservation} de {fecha_inicio} a {fecha_fin}'

    except Exception as e:
        return "Error durante scraping"
    finally:
        driver.quit()

     
@tool
def drop_playtomic_schedule(day_reservation: str, 
                            fecha_inicio: str, 
                            fecha_fin: str,
                            person_name: str) -> None:
    """
    Deletes an existing reservation from the Playtomic schedule for a specific time slot.

    This tool logs into Playtomic, navigates to the specified date, locates the reservation 
    matching the given time slot and person name, and deletes it from the schedule.
    It verifies that a reservation exists before attempting to remove it.

    Args:
        day_reservation (str): The specific date of the reservation in 'DD-MM-YYYY' format. Example '21-07-2025'
        fecha_inicio (str): The start time of the reservation in 'HH:MM' format. Example: '10:00'
        fecha_fin (str): The end time of the reservation in 'HH:MM' format. Example: '11:00'
        person_name (str): The exact name of the person whose reservation should be deleted. Example: 'Alejandro'

    Returns:
        str: A message indicating the success or failure of the deletion attempt.
    """

    driver = None
        
    schedule = playtomic_schedule()
    
    day_reservation_datetime = datetime.strptime(day_reservation,'%d-%m-%Y')    

    try: 
        
        time.sleep(5)
        
        driver = setup_driver()
        wait = WebDriverWait(driver, 20)
        
        is_within_schedule = check_is_within_schedule(fecha_inicio, fecha_fin)
        
        if not is_within_schedule:
            return f'Las reservas deben ser entre las 08:30 y las 22:00'
        
        is_valid_date = check_is_valid_date(day_reservation, fecha_inicio)
        
        if not is_valid_date:
            return f'Las reservas deben ser entre hoy y los proximos 14 días'
        
        if isinstance(schedule,str):
            return schedule
        elif isinstance(schedule,pd.DataFrame):
            is_any_match = check_reservation_exists(schedule, day_reservation_datetime, fecha_inicio, fecha_fin)
            if not is_any_match:
                return f"En la franja para el dia {day_reservation} de {fecha_inicio} a {fecha_fin} no existe ninguna reserva."
        
        login_playtomic(driver,wait)
        
        time.sleep(random.uniform(5,10))
        
        check_is_correct_schedule_date(driver,wait,day_reservation_datetime)
        
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, f"a.fc-time-grid-event")))
        
        time.sleep(3)
        
        for element in driver.find_elements(By.CSS_SELECTOR, f"a.fc-time-grid-event"):
            if person_name.lower() in str(element.text).lower() and fecha_inicio in element.text and fecha_fin in element.text:
                element.click()
                
        time.sleep(3)
        
        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Cancelar reserva']"))).click()
        
        time.sleep(3)

        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[span[text()='Cancelar partido']]"))).click()

        time.sleep(3)
        
        return f'Se ha eliminado la reserva del calendario para el dia {day_reservation} de {fecha_inicio} a {fecha_fin}'

    except Exception as e:
        return "Error durante scraping"
    finally:
        driver.quit()

@tool
def get_current_year() -> str:
    """
    Returns the year of the current date.
    """
    return datetime.now().year

@tool
def get_current_date() -> str:
    """
    Returns the current date
    """
    
    return datetime.now().strftime('%d-%m-%Y')