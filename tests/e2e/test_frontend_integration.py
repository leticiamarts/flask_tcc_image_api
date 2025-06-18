from pathlib import Path
from playwright.sync_api import sync_playwright

def test_streamlit_frontend_integration():
    test_image_path = Path("tests/assets/test.jpg")
    assert test_image_path.exists(), "Imagem de teste não encontrada."

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.goto("http://localhost:8501", timeout=30000)
        page.wait_for_selector("text=API de Processamento de Imagens")

        page.click("text=Escolha uma operação")
        page.click("text=rotacionar")

        page.get_by_role("slider").press("ArrowRight")

        page.set_input_files("input[type='file']", str(test_image_path))
        page.click("text=Enviar para processamento")

        page.wait_for_selector("img", timeout=60000)

        assert page.query_selector("text=Baixar imagem processada"), "Botão de download não encontrado."

        browser.close()
