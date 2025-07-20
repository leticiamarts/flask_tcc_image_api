from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

driver = webdriver.Chrome()

public_url = 'https://_____.ngrok-free.app/'

driver.get(public_url)

driver.set_script_timeout(1)

try:
    WebDriverWait(driver, 2).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Visit Site')]"))
    ).click()
    print("Popup fechado")
except:
    pass

try:
    upload = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]')))
    upload.send_keys(r'D:/projects/flask_tcc_image_api/simulate/assets/test_image2.png')
    print("Imagem carregada")
    
    time.sleep(1)
    
    send_btn = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.XPATH, '//button[contains(., "Enviar")]'))
    )
    
    for i in range(100):
        try:
            driver.execute_script("arguments[0].click();", send_btn)
            print(f"[{i+1}] Enviado")

            time.sleep(0.1)
            
        except Exception as e:
            print(f"Erro no envio {i+1}: {str(e)}")
            break
            
except Exception as e:
    print(f"Erro Crítico: {str(e)}")
finally:
    driver.quit()
    print("Teste concluído")