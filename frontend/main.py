import streamlit as st
from utils import montar_url, enviar_imagem

st.set_page_config(page_title="Processamento de Imagens", layout="centered")
st.title("🖼️ API de Processamento de Imagens")

operacao = st.selectbox("Escolha uma operação", ["rotacionar", "brilho", "contraste", "ruido", "recorte"])
params = {}

if operacao == "rotacionar":
    angle = st.slider("Ângulo de rotação", min_value=-180, max_value=180, value=90)
    params["angle"] = angle

elif operacao == "brilho":
    brightness = st.slider("Brilho", min_value=-100, max_value=100, value=30)
    params["brightness"] = brightness

elif operacao == "contraste":
    contrast = st.slider("Contraste", min_value=-100, max_value=100, value=50)
    params["contrast"] = contrast

elif operacao == "ruido":
    variance = st.slider("Intensidade do ruído (variância)", min_value=0, max_value=1000, value=625)
    params["var"] = variance

elif operacao == "recorte":
    x = st.number_input("X (posição horizontal)", min_value=0, value=50)
    y = st.number_input("Y (posição vertical)", min_value=0, value=50)
    w = st.number_input("Largura do recorte", min_value=1, value=100)
    h = st.number_input("Altura do recorte", min_value=1, value=100)
    params.update({"x": x, "y": y, "w": w, "h": h})

imagem = st.file_uploader("Envie uma imagem", type=["jpg", "jpeg", "png"])

if imagem and st.button("Enviar para processamento"):
    files = {"image": imagem}

    base_url = "http://flask-api/processar"
    url = montar_url(base_url, operacao, params)
    st.write(f"URL requisitada: {url}")

    try:
        response = enviar_imagem(url, files["image"])
        if response.status_code == 200:
            st.image(response.content, caption="Imagem processada")
            st.download_button(
                label="📥 Baixar imagem processada",
                data=response.content,
                file_name="imagem_processada.jpg",
                mime="image/jpeg"
            )
        else:
            st.error("Erro: " + response.text)
    except Exception as e:
        st.error(f"Erro ao conectar com a API: {e}")
