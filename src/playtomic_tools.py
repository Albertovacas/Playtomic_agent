import pandas as pd
import random
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException
import time
from langchain.tools import tool
from playtomic_utils import (playtomic_schedule,
                            login_playtomic,
                            setup_driver,
                            click_on_select_hour,
                            click_select_and_choose,
                            check_is_correct_date,
                            check_reservation_exists
                            )

@tool
def get_playtomic_schedule() -> str:
    """
    Retrieves the schedule of upcoming Playtomc reservations.
    Returns a Markdown-formatted table of active (non-cancelled) bookings,
    including the start date and end date of each match in YYYY-MM-DD HH:MM format.
    """
    
    schedule = playtomic_schedule()
    
    if isinstance(schedule,str):
        return schedule
    elif isinstance(schedule,pd.DataFrame):
        return "Reservas activas:\n" + reservation_df.astype(str).to_markdown(index=False)
        
        
def add_playtomic_schedule(day_reservation, fecha_inicio, fecha_fin, court_price, court_name) -> str:
        
    schedule = playtomic_schedule()
        
    try: 
        
        time.sleep(5)
        
        driver = setup_driver()
        wait = WebDriverWait(driver, 20)
        actions = ActionChains(driver)
        
        if isinstance(schedule,str):
            return schedule
        elif isinstance(schedule,pd.DataFrame):
            is_any_match = check_reservation_exists(schedule, day_reservation, fecha_inicio, fecha_fin)
            if is_any_match:
                return "La franja ya está ocupada."
        
        login_playtomic(driver,wait)
        
        time.sleep(random.uniform(5,10))
        
        check_is_correct_date(driver,wait,day_reservation)

        wait.until(EC.presence_of_element_located((By.XPATH, f"//tr[@data-time='{fecha_inicio}:00']")))
        
        click_on_select_hour(driver,actions,fecha_inicio)
        
        time.sleep(random.uniform(3,5))

        click_select_and_choose(wait,actions,"#startDate div.select__control", fecha_inicio)
        click_select_and_choose(wait,actions,"#endDate div.select__control", fecha_fin)

        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[span[text()='Editar']]"))).click()

        price_input = wait.until(EC.element_to_be_clickable((By.ID, "input-input-1")))
        price_input.clear()
        price_input.send_keys(court_price)
        
        time.sleep(random.uniform(3,5))

        input_field = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "input[id^='react-select'][id$='-input']")
        ))

        input_field.send_keys(court_name)

        option = wait.until(EC.element_to_be_clickable(
            (By.XPATH, f"//li//div[@class='ListItemContentstyles__CenterGroup-ny9mc5-2 iTqicv' and contains(., '{court_name}')]")
        ))
        option.click()
        
        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[span[text()='Crear']]"))).click()
        
        time.sleep(5)
        
        return 'Se ha añadido la reserva al calendario'

    except Exception as e:
        return "Error durante scraping"
    finally:
        driver.quit()