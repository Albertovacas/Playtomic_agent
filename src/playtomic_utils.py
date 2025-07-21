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
from typing import Union

import os
from dotenv import load_dotenv

import locale
locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')

load_dotenv()

email = os.getenv('EMAIL')
password = os.getenv('PASSWORD')

#Configuration of Selenium function
def setup_driver():
    options = webdriver.ChromeOptions()
    #options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument('--no-sandbox')
    options.add_argument('--user-agent=""Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.157 Safari/537.36""') # user agent
    
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    
    return driver
    
#Login in playtomic function
def login_playtomic(driver,wait):
    driver.get('https://manager.playtomic.io/auth/login')
    
    #Elimimar cookies
    driver.execute_script("""
    function hideCookies() {
        const selectors = [
            '#usercentrics-cmp-ui',
            'div[id*="cookie"]', 
            'div[class*="cookie"]',
            'iframe[title*="cookie"]',
            'aside[aria-label*="cookie"]'
        ];
        
        selectors.forEach(selector => {
            document.querySelectorAll(selector).forEach(el => el.remove());
        });
        
        document.body.style.overflow = 'auto';
    }
    hideCookies();
    setInterval(hideCookies, 1000);
    """ 
    )
    
    time.sleep(random.uniform(5,10))
    
    wait.until(EC.presence_of_element_located((By.NAME, "email")))

    driver.find_element(By.NAME, "email").send_keys(email)
    driver.find_element(By.NAME, "password").send_keys(password)
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))).click()
    
    time.sleep(random.uniform(5,10))
    
def playtomic_schedule() -> Union[str,pd.DataFrame]:
    
    driver = None
    
    try:
        driver = setup_driver()
        wait = WebDriverWait(driver, 20)
        
        login_playtomic(driver,wait)
        
        time.sleep(random.uniform(5,10))
        
        # Espera a que el menú de reservas esté presente
        wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Reservas"))).click()
        
        time.sleep(random.uniform(5,10))

        data, headers = [], []
        for _ in range(6):
            try:
                table = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "table.Tablestyles__Table-gx0hbp-0")))
                
                if not headers:
                    headers = [th.text for th in table.find_elements(By.CSS_SELECTOR, "thead th")]
            
                for row in table.find_elements(By.CSS_SELECTOR, "tbody tr"):
                    data.append([td.text for td in row.find_elements(By.TAG_NAME, "td")])
                    
                next_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Siguiente']")))
                next_button.click()
                time.sleep(random.uniform(5,10))
                    
            except TimeoutException:
                break
            except Exception as e:
                break
            
            if not data:
                return "No se encontraron reservas futuras o hubo un problema para cargarlas."

        reservation_df = pd.DataFrame(data, columns=headers)
        reservation_df = reservation_df[reservation_df.Estado != 'Cancelada']
        
        if reservation_df.empty:
            return "No hay reservas activas actualmente"
        
        reservation_df.loc[:,'start_dt'] = pd.to_datetime(reservation_df['Fecha de servicio'], dayfirst=True)
        reservation_df.loc[:,'fecha_reserva'] = reservation_df['start_dt'].dt.date
        reservation_df.loc[:,'hora_inicio'] = reservation_df['start_dt'].dt.strftime('%H:%M')

        dur = reservation_df['Duración'].str.replace('hr', 'h').str.replace(' min', 'm')
        reservation_df.loc[:,'dur_td'] = pd.to_timedelta(dur)
        reservation_df.loc[:,'end_dt'] = reservation_df['start_dt'] + reservation_df['dur_td']
        reservation_df.loc[:,'hora_fin'] = reservation_df['end_dt'].dt.strftime('%H:%M')
        
        return reservation_df

    except Exception as e:
        raise
    finally:
        driver.quit()
        
def calcular_fecha_fin(fecha_inicio, match_duration):
    fmt = "%H:%M"
    start = datetime.strptime(fecha_inicio, fmt)
    dur = timedelta(minutes=match_duration)
    end = start + dur
    return end.strftime(fmt)
        
def click_select_and_choose(wait, actions, selector_control, text):
    ctl = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector_control)))
    actions.move_to_element(ctl).click().perform()
    opt = wait.until(EC.element_to_be_clickable(
        (By.XPATH, f"//div[contains(@class,'select__option') and text()='{text}']")))
    opt.click()
    
def check_is_correct_date(driver,wait,day_reservation,days_to_check=7):
    
    for _ in range(days_to_check):
    
        # Suponiendo que ya tienes driver y wait definidos
        span = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "span.sc-kVhXZc.cueJXp")))
        current_date = span.text
        
        year = datetime.now().year 
        current_date_dt = datetime.strptime(f"{year}, {current_date}", f"%Y, %a, %d %b")
        
        if current_date_dt == day_reservation:
            break
        else:
            wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Siguiente']"))).click()
            time.sleep(random.uniform(5,10))
            
def check_reservation_exists(reservation_df, day_reservation, fecha_inicio, fecha_fin):
    
    dt_start = pd.Timestamp(f"{day_reservation.date()} {fecha_inicio}")
    dt_end = dt_start = pd.Timestamp(f"{day_reservation.date()} {fecha_fin}")
    
    FILTRO_START = (reservation_df['start_dt'] <= dt_start) & (dt_start < reservation_df['end_dt'])
    FILTRO_END = (reservation_df['start_dt'] < dt_end) & (dt_end <= reservation_df['end_dt'])
    is_any_match = len(reservation_df[FILTRO_START | FILTRO_END]) > 0
    
    return is_any_match


def click_on_select_hour(driver,actions,fecha_inicio):
    fecha_intermedio = calcular_fecha_fin(fecha_inicio, 15)
    fecha_destino = calcular_fecha_fin(fecha_inicio, 30)
    
    origen = driver.find_element(By.XPATH, f"//tr[@data-time='{fecha_inicio}:00']//td[@class='fc-widget-content']")
    intermedio = driver.find_element(By.XPATH, f"//tr[@data-time='{fecha_intermedio}:00']//td[@class='fc-widget-content']")
    destino = driver.find_element(By.XPATH, f"//tr[@data-time='{fecha_destino}:00']//td[@class='fc-widget-content']")
    
    casillas = [origen,intermedio,destino]
    
    # Empieza en la primera casilla
    actions.move_to_element(casillas[0]).click_and_hold()

    # Pasa por las demás casillas con el clic aún pulsado
    for casilla in casillas[1:]:
        actions.move_to_element(casilla)

    # Suelta el clic en la última
    actions.release().perform()
