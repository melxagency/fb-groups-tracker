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

# Esperar y hacer clic en Continue
    print('Buscando botón Continue...')
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    try:
        wait = WebDriverWait(driver, 10)
        btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[text()="Continue"]')))
        btn.click()
        print('✅ Clic en Continue (texto)')
        time.sleep(5)
    except:
        try:
            # Intentar por JavaScript esperando que el elemento exista
            for _ in range(5):
                resultado = driver.execute_script("""
                    const elements = document.querySelectorAll('*');
                    for (const el of elements) {
                        if (el.innerText && (el.innerText.trim() === 'Continue' || el.innerText.trim() === 'Continuar')) {
                            el.click();
                            return true;
                        }
                    }
                    return false;
                """)
                if resultado:
                    print('✅ Clic via JavaScript')
                    time.sleep(5)
                    break
                time.sleep(2)
        except Exception as e:
            print(f'⚠️ No se pudo hacer clic en Continue: {e}')

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
