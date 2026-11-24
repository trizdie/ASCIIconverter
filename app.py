"""Gerador de arte ASCII: recebe uma imagem por upload e devolve a arte em texto."""

from flask import Flask, jsonify, request, send_from_directory
from PIL import Image, ImageOps, UnidentifiedImageError

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB por upload

# Rampas de caracteres, do mais "vazio" para o mais "denso".
RAMPAS = {
    "detalhado": " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$",
    "simples": " .:-=+*#%@",
    "blocos": " ░▒▓█",
    "minimo": " .oO@",
}

# Caracteres de fonte monoespaçada são ~2x mais altos que largos.
PROPORCAO_CARACTERE = 0.55
LARGURA_MIN, LARGURA_MAX = 10, 300


def inteiro_no_intervalo(valor, padrao, minimo, maximo):
    try:
        return max(minimo, min(maximo, int(valor)))
    except (TypeError, ValueError):
        return padrao


def imagem_para_ascii(img, largura, rampa, fundo_escuro, colorido):
    img = ImageOps.exif_transpose(img)

    # Achata transparência sobre a cor do fundo escolhido.
    img = img.convert("RGBA")
    cor_fundo = (0, 0, 0, 255) if fundo_escuro else (255, 255, 255, 255)
    img = Image.alpha_composite(Image.new("RGBA", img.size, cor_fundo), img).convert("RGB")

    w, h = img.size
    altura = max(1, round(h / w * largura * PROPORCAO_CARACTERE))
    img = img.resize((largura, altura), Image.Resampling.LANCZOS)

    cinza = ImageOps.autocontrast(img.convert("L"), cutoff=1).tobytes()
    n = len(rampa)

    def caractere(brilho):
        # Fundo escuro: pixel claro vira caractere denso. Fundo claro: o inverso.
        nivel = brilho if fundo_escuro else 255 - brilho
        return rampa[nivel * (n - 1) // 255]

    linhas = [
        "".join(caractere(v) for v in cinza[y * largura:(y + 1) * largura])
        for y in range(altura)
    ]

    cores = None
    if colorido:
        hex_total = img.tobytes().hex()
        tam = largura * 6
        cores = [hex_total[y * tam:(y + 1) * tam] for y in range(altura)]

    return "\n".join(linhas), altura, cores


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.post("/api/ascii")
def gerar():
    arquivo = request.files.get("imagem")
    if arquivo is None or arquivo.filename == "":
        return jsonify(erro="Envie uma imagem no campo 'imagem'."), 400

    largura = inteiro_no_intervalo(request.form.get("largura"), 100, LARGURA_MIN, LARGURA_MAX)
    rampa = RAMPAS.get(request.form.get("conjunto", "detalhado"), RAMPAS["detalhado"])
    fundo_escuro = request.form.get("fundo", "escuro") != "claro"
    colorido = request.form.get("colorido") == "1"

    try:
        img = Image.open(arquivo.stream)
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        return jsonify(erro="Arquivo inválido ou não é uma imagem suportada."), 400

    texto, altura, cores = imagem_para_ascii(img, largura, rampa, fundo_escuro, colorido)
    return jsonify(texto=texto, largura=largura, altura=altura, cores=cores)


@app.errorhandler(413)
def arquivo_grande(_):
    return jsonify(erro="Imagem muito grande (máximo 10 MB)."), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
