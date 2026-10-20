import os
import io
import base64
import uuid
import random

from flask import Flask, render_template, request, session, url_for
from PIL import Image

import numpy as np
import matplotlib
matplotlib.use("Agg")  # важно: серверная генерация без GUI
import matplotlib.pyplot as plt

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "bmp"}
MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 МБ

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def new_captcha() -> str:
    """Простая арифметическая капча. Ответ хранится в session."""
    a = random.randint(2, 9)
    b = random.randint(2, 9)
    session["captcha_answer"] = a + b
    return f"{a} + {b}"


def swap_halves(img: Image.Image, mode: str) -> Image.Image:
    """mode='lr' — лево/право, mode='tb' — верх/низ."""
    img = img.convert("RGB")
    w, h = img.size
    result = Image.new("RGB", (w, h))

    if mode == "lr":
        mid = w // 2
        left = img.crop((0, 0, mid, h))
        right = img.crop((mid, 0, w, h))
        result.paste(right, (0, 0))
        result.paste(left, (w - mid, 0))
    elif mode == "tb":
        mid = h // 2
        top = img.crop((0, 0, w, mid))
        bottom = img.crop((0, mid, w, h))
        result.paste(bottom, (0, 0))
        result.paste(top, (0, h - mid))
    else:
        result = img.copy()
    return result


def make_color_histogram(original: Image.Image, result: Image.Image) -> str:
    """Строит графики R/G/B для обоих изображений, возвращает base64 PNG."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    for ax, img, title in zip(
        axes,
        [original.convert("RGB"), result.convert("RGB")],
        ["Исходное изображение", "Результат"],
    ):
        arr = np.array(img)
        for channel, color in enumerate(["r", "g", "b"]):
            hist, _ = np.histogram(arr[:, :, channel], bins=256, range=(0, 256))
            ax.plot(hist, color=color, alpha=0.8, label=color.upper())
        ax.set_title(title)
        ax.set_xlabel("Интенсивность цвета")
        ax.set_ylabel("Количество пикселей")
        ax.grid(alpha=0.3)
        ax.legend()

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        session["captcha_q"] = new_captcha()
        return render_template("index.html", captcha_q=session["captcha_q"])

    captcha_q = session.get("captcha_q", "")
    expected = session.get("captcha_answer")
    user_answer = request.form.get("captcha", "").strip()

    if not expected or not user_answer.isdigit() or int(user_answer) != expected:
        session["captcha_q"] = new_captcha()
        return render_template(
            "index.html",
            captcha_q=session["captcha_q"],
            error="Неверный ответ на капчу. Попробуйте ещё раз.",
        )

    mode = request.form.get("mode", "lr")
    file = request.files.get("image")

    if not file or file.filename == "":
        session["captcha_q"] = new_captcha()
        return render_template(
            "index.html", captcha_q=session["captcha_q"], error="Выберите файл изображения."
        )

    if not allowed_file(file.filename):
        session["captcha_q"] = new_captcha()
        return render_template(
            "index.html",
            captcha_q=session["captcha_q"],
            error="Недопустимый формат файла. Разрешены PNG, JPG, JPEG, GIF, BMP.",
        )

    try:
        img = Image.open(file.stream).convert("RGB")
    except Exception:
        session["captcha_q"] = new_captcha()
        return render_template(
            "index.html",
            captcha_q=session["captcha_q"],
            error="Не удалось открыть изображение. Проверьте файл.",
        )

    img.thumbnail((1600, 1600))

    uid = uuid.uuid4().hex
    original_name = f"original_{uid}.png"
    result_name = f"result_{uid}.png"

    original_path = os.path.join(app.config["UPLOAD_FOLDER"], original_name)
    result_path = os.path.join(app.config["UPLOAD_FOLDER"], result_name)

    img.save(original_path, "PNG")
    result_img = swap_halves(img, mode)
    result_img.save(result_path, "PNG")

    hist_b64 = make_color_histogram(img, result_img)
    session["captcha_q"] = new_captcha()

    return render_template(
        "index.html",
        captcha_q=session["captcha_q"],
        original_url=url_for("static", filename=f"uploads/{original_name}"),
        result_url=url_for("static", filename=f"uploads/{result_name}"),
        hist_b64=hist_b64,
        mode=mode,
    )


@app.errorhandler(413)
def too_large(e):
    session["captcha_q"] = new_captcha()
    return render_template(
        "index.html",
        captcha_q=session["captcha_q"],
        error="Файл слишком большой. Максимальный размер — 8 МБ.",
    ), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)