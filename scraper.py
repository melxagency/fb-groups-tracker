import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from supabase import create_client
from dotenv import load_dotenv
import os
import time
import re
import json

load_dotenv()

supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

COOKIES_FILE = os.path.abspath(os.path.join('cookies', 'facebook_cookies.json'))
CONTINUE_BTN_XPATH = '//*[@class="x1i10hfl xjbqb8w x1ejq31n x18oe1m7 x1sy0etr xstzfhl x972fbf x10w94by x1qhh985 x14e42zd x1ypdohk x3ct3a4 xdj266r x14z9mp xat24cr x1lziwak xexx8yu xyri2b x18d9i69 x1c1uobl x16tdsg8 x1hl2dhg xggy1nq x1fmog5m xu25z0z x140muxe xo1y3bh x87ps6o x1lku1pv x1a2a7pz x9f619 x3nfvp2 xdt5ytf xl56j7k x1n2onr6 xh8yej3"]'
PASSWORD_INPUT_XPATH = '//*[@class="x1i10hfl xggy1nq xtpw4lu x1tutvks x1s3xk63 x1s07b3s x1a2a7pz xjbqb8w x1v8p93f x1o3jo1z x16stqrj xv5lvn5 x1ejq31n x18oe1m7 x1sy0etr xstzfhl x972fbf x10w94by x1qhh985 x14e42zd x9f619 xzsf02u x1lliihq x15h3p50 x10emqs4 x1vr9vpq x1iyjqo2 x10d0gm4 x1fhayk4 x16wdlz0 x3cjxhe xe9ewy2 x11lt19s xeuugli xlyipyv x1hcrkkg xfvqz1d x12vv892 x1hu168l xttzon8 x1sfh74k x3fqe8q x185fvkj x1p97g3g xmtqnhx x11ig0mb xgmu6d7 x1quw8ve xx0ingd xdj266r xyiysdx x14vy60q x109j2v6 xp5op4 x1y44fgy xdzva22 xs8nzd4 x1fzehxr xha3pab"]'

def click_continue_if_present(driver):
    try:
        btn = driver.find_element(By.XPATH, CONTINUE_BTN_XPATH)
        btn.click()
        print('  ✅ Clic en Continue')
        time.sleep(4)
        return True
    except:
        return False

def handle_password_modal(driver):
    try:
        pwd_inputs = driver.find_elements(By.XPATH, PASSWORD_INPUT_XPATH)
        if not pwd_inputs:
            return False

        pwd_input = pwd_inputs[0]
        pwd_input.click()
        time.sleep(1)
        pwd_input.send_keys(os.getenv('FB_PASSWORD'))
        time.sleep(1)
        print('  ✅ Password escrito')

        # Presionar Enter directamente — más confiable que buscar el botón
        pwd_input.send_keys(Keys.RETURN)
        print('  ✅ Enter presionado en password')
        time.sleep(7)
        return True
    except Exception as e:
        print(f'  ⚠️ Error en modal: {e}')
        return False

def handle_facebook_screens(driver):
    # 1. Intentar password primero
    if handle_password_modal(driver):
        time.sleep(3)

    # 2. Luego Continue si aparece
    if click_continue_if_present(driver):
        time.sleep(3)
        # 3. Si después del Continue aparece password
        if handle_password_modal(driver):
            time.sleep(3)

def load_cookies(driver):
    if not os.path.exists(COOKIES_FILE):
        print('❌ No hay cookies - ejecuta login.py primero')
        return False

    with open(COOKIES_FILE, 'r') as f:
        cookies = json.load(f)

    print('Navegando a Facebook...')
    driver.get('https://www.facebook.com/')
    time.sleep(5)
    print(f'URL inicial: {driver.current_url}')

    for cookie in cookies:
        cookie.pop('sameSite', None)
        cookie.pop('expiry', None)
        if 'facebook.com' in cookie.get('domain', ''):
            try:
                driver.add_cookie(cookie)
            except:
                pass

    print(f'✅ {len(cookies)} cookies cargadas')

    print('Recargando con cookies...')
    driver.get('https://www.facebook.com/?sk=h_chr')
    time.sleep(6)
    print(f'URL después de cookies: {driver.current_url}')

    handle_facebook_screens(driver)

    print(f'URL final load_cookies: {driver.current_url}')
    return True

def is_logged_in(driver):
    return 'login' not in driver.current_url and 'checkpoint' not in driver.current_url

def parse_members(text):
    text = text.lower().strip()
    match = re.search(r'([\d,.]+)\s*(mil)?', text)
    if not match:
        return None
    num = float(match.group(1).replace(',', '.'))
    if match.group(2):
        num *= 1000
    return round(num)

def get_member_count(driver, group_url, nombre='grupo'):
    try:
        driver.get(group_url)
        time.sleep(6)

        handle_facebook_screens(driver)
        time.sleep(2)

        en_github = os.getenv('GITHUB_ACTIONS') == 'true'
        if en_github:
            os.makedirs('debug', exist_ok=True)
            nombre_limpio = re.sub(r'[^\w]', '_', nombre)[:30]
            driver.save_screenshot(f'debug/{nombre_limpio}.png')
            with open(f'debug/{nombre_limpio}.html', 'w', encoding='utf-8') as f:
                f.write(driver.page_source)

        elements = driver.find_elements(
            By.XPATH,
            '//*[contains(text(), "miembros") or contains(text(), "members")]'
        )
        for el in elements:
            text = el.text.strip()
            if re.search(r'[\d,.]+\s*(mil\s*)?(miembros|members)', text, re.IGNORECASE):
                count = parse_members(text)
                if count:
                    return count
        return None
    except Exception as e:
        print(f'  Error en {group_url}: {e}')
        return None

def main():
    response = supabase.table('facebook_groups').select('id, nombre, link').execute()
    grupos = response.data
    print(f'Grupos encontrados: {len(grupos)}')

    en_github = os.getenv('GITHUB_ACTIONS') == 'true'
    chrome_path = os.getenv('CHROME_PATH', None)

    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--lang=es-ES')
    options.add_argument('--window-size=1920,1080')

    if en_github:
        options.add_argument('--headless=new')
        options.add_argument('--disable-gpu')
        print('🤖 Modo GitHub Actions (headless)')
    else:
        print('💻 Modo local (con ventana)')

    driver = uc.Chrome(
        options=options,
        use_subprocess=True,
        browser_executable_path=chrome_path
    )

    try:
        print('Cargando cookies...')
        cookies_ok = load_cookies(driver)

        if not cookies_ok:
            return

        if not is_logged_in(driver):
            print('❌ Sesión expirada - ejecuta login.py localmente y actualiza el secret FB_COOKIES en GitHub')
            exit(1)

        print('✅ Sesión activa')

        print(f'\nProcesando {len(grupos)} grupos...\n')
        resultados = []

        for grupo in grupos:
            print(f'Scraping: {grupo["nombre"]}')
            miembros = get_member_count(driver, grupo['link'], grupo['nombre'])

            if miembros:
                supabase.table('facebook_groups')\
                    .update({'miembros_actuales': miembros})\
                    .eq('id', grupo['id'])\
                    .execute()
                print(f'  ✅ {miembros:,} miembros')
                resultados.append({'nombre': grupo['nombre'], 'miembros': miembros, 'ok': True})
            else:
                print(f'  ⚠️ No se pudo obtener miembros')
                resultados.append({'nombre': grupo['nombre'], 'miembros': None, 'ok': False})

            time.sleep(3)

    finally:
        driver.quit()

    exitosos = len([r for r in resultados if r['ok']])
    fallidos = len([r for r in resultados if not r['ok']])
    print(f'\n══════════════════════════════')
    print(f'RESUMEN FINAL')
    print(f'══════════════════════════════')
    print(f'✅ Exitosos: {exitosos}')
    print(f'❌ Fallidos: {fallidos}')
    print(f'══════════════════════════════')

    if exitosos == 0:
        exit(1)

if __name__ == '__main__':
    main()
