import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
import os
import time
import json

load_dotenv()

COOKIES_FILE = os.path.abspath(os.path.join('cookies', 'facebook_cookies.json'))

def save_cookies(driver):
    os.makedirs('cookies', exist_ok=True)
    cookies = driver.get_cookies()
    with open(COOKIES_FILE, 'w') as f:
        json.dump(cookies, f, indent=2)
    print(f'✅ {len(cookies)} cookies guardadas en cookies/facebook_cookies.json')

def main():
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--lang=es-ES')

    driver = uc.Chrome(options=options, use_subprocess=True)
    wait = WebDriverWait(driver, 15)

    print('Abriendo Facebook...')
    driver.get('https://www.facebook.com/')
    time.sleep(3)

    # Aceptar cookies si aparece
    try:
        cookie_btn = driver.find_element(By.XPATH, '//*[@data-cookiebanner="accept_button"]')
        cookie_btn.click()
        time.sleep(2)
    except:
        pass

    # Email
    email_element = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@name="email"]')))
    email_element.click()
    email_element.send_keys(os.getenv('FB_EMAIL'))
    time.sleep(1)

    # Password
    pass_element = driver.find_element(By.XPATH, '//*[@name="pass"]')
    pass_element.click()
    pass_element.send_keys(os.getenv('FB_PASSWORD'))
    time.sleep(1)

    # Login button - usar submit en vez de clase CSS
    login_element = driver.find_element(By.XPATH, '//*[@class="x1i10hfl xjbqb8w x1ejq31n x18oe1m7 x1sy0etr xstzfhl x972fbf x10w94by x1qhh985 x14e42zd x1ypdohk x3ct3a4 xdj266r x14z9mp xat24cr x1lziwak xexx8yu xyri2b x18d9i69 x1c1uobl x16tdsg8 x1hl2dhg xggy1nq x1fmog5m xu25z0z x140muxe xo1y3bh x87ps6o x1lku1pv x1a2a7pz x9f619 x3nfvp2 xdt5ytf xl56j7k x1n2onr6 xh8yej3"]')
    login_element.click()

    print('⏳ Tienes 120 segundos para completar el 2FA...')
    time.sleep(60)

    if 'login' not in driver.current_url and 'checkpoint' not in driver.current_url:
        print('✅ Login exitoso, guardando cookies...')
        save_cookies(driver)
        time.sleep(2)  # asegurar que se guarde antes de cerrar
        print('✅ Listo, ya puedes ejecutar scraper.py')
    else:
        print('❌ Login fallido o 2FA no completado a tiempo')

    driver.quit()

if __name__ == '__main__':
    main()