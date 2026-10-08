import base64
import io
import os
import re
from urllib.parse import quote
from flask import Flask, jsonify, render_template, request, send_from_directory
from PIL import Image, ImageColor
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers.pil import (
    CircleModuleDrawer,
    GappedSquareModuleDrawer,
    RoundedModuleDrawer,
    SquareModuleDrawer,
)

try:
    from qrcode.image.styles.moduledrawers.pil import VerticalBarsModuleDrawer
except ImportError:
    VerticalBarsModuleDrawer = SquareModuleDrawer

try:
    from qrcode.image.styles.moduledrawers.pil import HorizontalBarsModuleDrawer
except ImportError:
    HorizontalBarsModuleDrawer = SquareModuleDrawer

app = Flask(__name__)

MODULE_DRAWERS = {
    "square": SquareModuleDrawer(),
    "circle": CircleModuleDrawer(),
    "rounded": RoundedModuleDrawer(),
    "gapped": GappedSquareModuleDrawer(),
    "vertical": VerticalBarsModuleDrawer(),
    "horizontal": HorizontalBarsModuleDrawer(),
}


def sanitize_color(color_str, default_color="#000000"):
    if not color_str:
        return default_color
    color_str = color_str.strip()
    if re.match(r"^([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$", color_str):
        color_str = f"#{color_str}"
    if re.match(r"^#([0-9A-Fa-f]{3})$", color_str):
        c = color_str
        color_str = f"#{c[1]}{c[1]}{c[2]}{c[2]}{c[3]}{c[3]}"
    if re.match(r"^#[0-9A-Fa-f]{6}$", color_str):
        return color_str.upper()
    return default_color


def build_payload_from_dict(qr_type, data):
    if qr_type == "wifi":
        ssid = data.get("wifi_ssid", "").strip()
        password = data.get("wifi_password", "").strip()
        security = data.get("wifi_security", "WPA").strip()
        if not ssid:
            return None
        return f"WIFI:T:{security};S:{ssid};P:{password};;"
    elif qr_type == "whatsapp":
        phone = re.sub(r"\D", "", data.get("wa_phone", ""))
        message = data.get("wa_message", "").strip()
        if not phone:
            return None
        encoded_msg = f"?text={quote(message)}" if message else ""
        return f"https://wa.me/{phone}{encoded_msg}"
    elif qr_type == "vcard":
        name = data.get("vcard_name", "").strip()
        phone = data.get("vcard_phone", "").strip()
        email = data.get("vcard_email", "").strip()
        org = data.get("vcard_org", "").strip()
        if not name and not phone:
            return None
        return f"BEGIN:VCARD\nVERSION:3.0\nFN:{name}\nTEL:{phone}\nEMAIL:{email}\nORG:{org}\nEND:VCARD"
    else:
        return data.get("link", "").strip()


def make_background_transparent(img, back_color_hex):
    img = img.convert("RGBA")
    try:
        bg_rgb = ImageColor.getrgb(back_color_hex)
    except Exception:
        bg_rgb = (255, 255, 255)

    datas = img.getdata()
    new_data = []
    for item in datas:
        if abs(item[0] - bg_rgb[0]) < 15 and abs(item[1] - bg_rgb[1]) < 15 and abs(item[2] - bg_rgb[2]) < 15:
            new_data.append((0, 0, 0, 0))
        else:
            new_data.append(item)

    img.putdata(new_data)
    return img


# Rota explícita para entregar o favicon a partir de static/favicon.svg
@app.route("/favicon.ico")
@app.route("/favicon.svg")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "favicon.svg",
        mimetype="image/svg+xml",
    )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/qr", methods=["POST"])
def generate_qr():
    if request.is_json:
        data = request.get_json(silent=True) or {}
        qr_type = data.get("type", "url")
        payload = build_payload_from_dict(qr_type, data)
        fill_color = sanitize_color(data.get("fill_color"), "#000000")
        back_color = sanitize_color(data.get("back_color"), "#FFFFFF")
        module_style = data.get("module_style", "square")
        transparent_bg = str(data.get("transparent_bg", "")).lower() in ["true", "on", "1"]
        box_size_raw = data.get("box_size", 10)
        box_size = int(box_size_raw) if str(box_size_raw).isdigit() else 10
        logo_file = None
    else:
        form = request.form
        qr_type = form.get("type", "url")
        payload = build_payload_from_dict(qr_type, form)
        fill_color = sanitize_color(form.get("fill_color"), "#000000")
        back_color = sanitize_color(form.get("back_color"), "#FFFFFF")
        module_style = form.get("module_style", "square")
        transparent_bg = form.get("transparent_bg") in ["true", "on", "1"]
        try:
            box_size = int(form.get("box_size", 10))
        except (ValueError, TypeError):
            box_size = 10
        logo_file = request.files.get("logo")

    if not payload:
        return jsonify({"error": "Preencha os campos obrigatórios."}), 400

    try:
        has_logo = logo_file and logo_file.filename != ""
        error_correction = (
            qrcode.constants.ERROR_CORRECT_H if has_logo else qrcode.constants.ERROR_CORRECT_M
        )

        qr = qrcode.QRCode(
            version=None,
            error_correction=error_correction,
            box_size=box_size,
            border=4,
        )
        qr.add_data(payload)
        qr.make(fit=True)

        drawer = MODULE_DRAWERS.get(module_style, SquareModuleDrawer())

        img = qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=drawer,
            fill_color=fill_color,
            back_color=back_color,
        ).convert("RGBA")

        if transparent_bg:
            img = make_background_transparent(img, back_color)

        if has_logo:
            logo = Image.open(logo_file.stream)
            qr_w, qr_h = img.size
            max_logo_size = int(qr_w * 0.22)
            logo.thumbnail((max_logo_size, max_logo_size), Image.Resampling.LANCZOS)
            logo_w, logo_h = logo.size
            pos = ((qr_w - logo_w) // 2, (qr_h - logo_h) // 2)

            if logo.mode == "RGBA":
                img.paste(logo, pos, logo)
            else:
                img.paste(logo, pos)

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return jsonify({"success": True, "image": f"data:image/png;base64,{img_base64}"})

    except Exception as e:
        return jsonify({"error": f"Erro ao gerar QR Code: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)