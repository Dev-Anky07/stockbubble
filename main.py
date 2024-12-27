import time
import json
import re
import csv
import os
import requests
from time import sleep
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException

def setup_driver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def load_cookies(driver, cookie_file):
    with open(cookie_file, 'r') as f:
        cookies_dict = json.load(f)
    for cookie in cookies_dict['cookies']:
        cookie['sameSite'] = 'None'
        if 'id' in cookie:
            del cookie['id']
        driver.add_cookie(cookie)

def take_screenshot(driver, format='png'):
    filename = f"/tmp/ss.{format}"  # Using /tmp directory in Lambda
    driver.save_screenshot(filename)
    return filename

def get_advance_decline_values_xpath(driver):
    try:
        parent_xpath = '//*[@id="NIFTY50"]/div/div/div[1]/div[2]/div/div[2]/div[2]'
        parent_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, parent_xpath))
        )
        
        advances_xpath = './/li[@class="advances"]/span[2]'
        advances_element = parent_element.find_element(By.XPATH, advances_xpath)
        num_adv = int(advances_element.text)
        
        declines_xpath = './/li[@class="declines"]/span[2]'
        declines_element = parent_element.find_element(By.XPATH, declines_xpath)
        num_dec = int(declines_element.text)
        
        return num_adv, num_dec
    except Exception as e:
        print(f"Error extracting values: {e}")
        return None, None

def get_fii_dii_values_xpath(driver):
    try:
        
        base_xpath = '/html/body/section/div/div[4]/div[1]/div/div[1]/div/div/table'
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, base_xpath))
        )
        
        # Extract net FII value (4th cell of first tbody row)
        net_fii_xpath = base_xpath + '/tbody/tr[1]/td[4]'
        net_fii_element = driver.find_element(By.XPATH, net_fii_xpath)
        net_fii = float(net_fii_element.text.replace(',', ''))
        
        # Extract net DII value (7th cell of first tbody row)
        net_dii_xpath = base_xpath + '/tbody/tr[1]/td[7]'
        net_dii_element = driver.find_element(By.XPATH, net_dii_xpath)
        net_dii = float(net_dii_element.text.replace(',', ''))
        
        print(f"Found values - FII: {net_fii}, DII: {net_dii}")
        return net_fii, net_dii

    except Exception as e:
        print(f"Error extracting FII/DII values: {e}")
        print(f"Current URL: {driver.current_url}")  # Debug print
        return None, None

def format_fii_dii_message(fii_value, dii_value):
    fii_action = "Buy" if fii_value > 0 else "Sell"
    dii_action = "Buy" if dii_value > 0 else "Sell"
    fii_dir = "Inflow" if fii_value > 0 else "Outflow"
    dii_dir = "Inflow" if dii_value > 0 else "Outflow"
    #fii_dir = "🟢" if fii_value > 0 else "🔴"
    #dii_dir = "🟢" if dii_value > 0 else "🔴"
    
    fii_formatted = f"Net FII {fii_action}: {abs(fii_value)} CR {fii_dir}"
    dii_formatted = f"Net DII {dii_action}: {abs(dii_value)} CR {dii_dir}"
    
    return fii_formatted, dii_formatted

def main():
    driver = setup_driver()
    try:

        # StockBubble screenshot
        driver.get('https://stockbubble.in/')
        time.sleep(5)
        screenshot_file = take_screenshot(driver)
            
        # Get advances/declines
        driver.get('https://www.nseindia.com/')
        time.sleep(2)
        num_adv, num_dec = get_advance_decline_values_xpath(driver)
            
        # Get FII/DII data
        driver.get('https://www.moneycontrol.com/stocks/marketstats/fii_dii_activity/index.php')
        time.sleep(3)
        net_fii, net_dii = get_fii_dii_values_xpath(driver)
        try:
            driver.get('https://x.com/i/flow/login')
            load_cookies(driver, 'x.json')  # Adjust path as needed
            driver.refresh()
            driver.get('https://x.com/compose/post')
                
            tweet_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="tweetTextarea_0"]'))
            )
                
            fii_message, dii_message = format_fii_dii_message(net_fii, net_dii)
            message = (
                f"Advances : {num_adv} & Declines : {num_dec} in Nifty50\n\n"
                f"{fii_message} and {dii_message}"
            )
            tweet_box.send_keys(message)
            print(message)
            # Upload screenshot
            media_button = driver.find_element(By.CSS_SELECTOR, '[data-testid="fileInput"]')
            media_button.send_keys(screenshot_file)
                
            time.sleep(3)
            post_button = driver.find_element(By.CSS_SELECTOR, '[data-testid="tweetButton"]')
            post_button.click()
            time.sleep(30)
            #driver.quit()
        except Exception as e:
            print(f"Error posting tweet: {e}")
    finally:
        print('Run complete')
        #driver.quit()

if __name__ == "__main__":
    main()