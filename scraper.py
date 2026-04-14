import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
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

def load_cookies(driver):
    if not os.path.exists(COOKIES_FILE):
        print('❌ No hay cookies - ejecuta login.py primero')
        return False

    with open(COOKIES_FILE, 'r') as f:
        cookies = json.load(f)

    driver.get('https://www.facebook.com/')
    time.sleep(5)

    for cookie in cookies:
        cookie.pop('sameSite', None)
        cookie.pop('expiry', None)
        if 'facebook.com' in cookie.get('domain', ''):
            try:
                driver.add_cookie(cookie)
            except:
                pass

    print(f'✅ {len(cookies)} cookies cargadas')

    driver.get('https://www.facebook.com/')
    time.sleep(5)

    # Estrategia 1: por texto exacto en cualquier elemento clickeable
    btn = driver.find_element(By.XPATH, '//*[@class="x1i10hfl xjbqb8w x1ejq31n x18oe1m7 x1sy0etr xstzfhl x972fbf x10w94by x1qhh985 x14e42zd x1ypdohk x3ct3a4 xdj266r x14z9mp xat24cr x1lziwak xexx8yu xyri2b x18d9i69 x1c1uobl x16tdsg8 x1hl2dhg xggy1nq x1fmog5m xu25z0z x140muxe xo1y3bh x87ps6o x1lku1pv x1a2a7pz x9f619 x3nfvp2 xdt5ytf xl56j7k x1n2onr6 xh8yej3"]')
    btn.click()
          

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
