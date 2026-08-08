import io
import base64
import html
from urllib.parse import urlparse

import streamlit as st
import qrcode

from qrcode.constants import ERROR_CORRECT_H
from qrcode.image.styledpil import StyledPilImage

from qrcode.image.styles.moduledrawers.pil import (
    SquareModuleDrawer,
    RoundedModuleDrawer,
    CircleModuleDrawer,
)

from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Branded QR Generator",
    page_icon="🔳",
    layout="wide",
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>
    .main-title {
        font-size: 38px;
        font-weight: 700;
        margin-bottom: 5px;
    }

    .subtitle {
        color: #666;
        font-size: 16px;
        margin-bottom: 25px;
    }

    .preview-box {
        background: #f7f7f7;
        border-radius: 15px;
        padding: 30px;
        text-align: center;
        border: 1px solid #e5e5e5;
    }

    .safety-good {
        background: #e8f7ed;
        color: #146c2e;
        padding: 12px;
        border-radius: 8px;
        margin-top: 10px;
    }

    .safety-warning {
        background: #fff3cd;
        color: #856404;
        padding: 12px;
        border-radius: 8px;
        margin-top: 10px;
    }

    .small-note {
        color: #666;
        font-size: 13px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HELPERS
# ============================================================

def hex_to_rgb(hex_color: str):
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        raise ValueError("Hex color must be 6 characters long.")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def hex_to_rgba(hex_color: str, alpha: int = 255):
    r, g, b = hex_to_rgb(hex_color)
    return (r, g, b, alpha)


def relative_luminance(rgb):
    values = []

    for value in rgb:
        value = value / 255
        if value <= 0.03928:
            value = value / 12.92
        else:
            value = ((value + 0.055) / 1.055) ** 2.4
        values.append(value)

    return (
        0.2126 * values[0]
        + 0.7152 * values[1]
        + 0.0722 * values[2]
    )


def contrast_ratio(color1: str, color2: str):
    lum1 = relative_luminance(hex_to_rgb(color1))
    lum2 = relative_luminance(hex_to_rgb(color2))

    return (max(lum1, lum2) + 0.05) / (min(lum1, lum2) + 0.05)


def validate_url(url: str):
    try:
        parsed = urlparse(url.strip())
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except ValueError:
        return False


def get_logo_background_fill(mode: str, background_color: str):
    if mode == "White":
        return (255, 255, 255, 255)
    if mode == "Same as QR background":
        return hex_to_rgba(background_color, 255)
    return None


# ============================================================
# FONT HELPERS
# ============================================================

def get_font(size: int):
    font_paths = [
        "arial.ttf",
        "Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ]

    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass

    return ImageFont.load_default()


def get_fitting_font_and_size(text: str, max_width: int, start_size: int):
    dummy = Image.new("RGBA", (20, 20), (255, 255, 255, 0))
    draw = ImageDraw.Draw(dummy)

    min_size = 12
    for size in range(start_size, min_size - 1, -1):
        font = get_font(size)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        if text_width <= max_width:
            return font, size, bbox

    font = get_font(min_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    return font, min_size, bbox


# ============================================================
# QR STYLE (PIL PREVIEW / PNG / PDF)
# ============================================================

def get_module_drawer(style: str):
    if style == "Rounded":
        return RoundedModuleDrawer()

    if style == "Dots":
        return CircleModuleDrawer()

    return SquareModuleDrawer()



# ============================================================
# QR GENERATION
# ============================================================

def create_qr_object(url: str):
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_H,
        box_size=20,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    return qr


def generate_qr_image(
    qr_obj,
    qr_color: str,
    background_color: str,
    module_style: str,
):
    qr_image = qr_obj.make_image(
        image_factory=StyledPilImage,
        module_drawer=get_module_drawer(module_style),
        fill_color=qr_color,
        back_color=background_color,
    )

    return qr_image.convert("RGBA")


# ============================================================
# LOGO
# ============================================================

def add_logo(
    qr_image,
    logo_image,
    logo_percentage: int,
    logo_background_mode: str,
    background_color: str,
):
    qr_image = qr_image.copy()
    width, height = qr_image.size

    safe_percentage = min(max(int(logo_percentage), 5), 25)
    target_size = int(min(width, height) * safe_percentage / 100)

    logo = logo_image.copy().convert("RGBA")
    logo.thumbnail((target_size, target_size), Image.Resampling.LANCZOS)

    center_x = (width - logo.width) // 2
    center_y = (height - logo.height) // 2

    background_fill = get_logo_background_fill(
        logo_background_mode,
        background_color,
    )

    if background_fill is None:
        qr_image.alpha_composite(logo, (center_x, center_y))
        return qr_image

    padding = max(12, int(target_size * 0.12))
    box_width = logo.width + (padding * 2)
    box_height = logo.height + (padding * 2)

    logo_box = Image.new("RGBA", (box_width, box_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(logo_box)

    radius = max(10, int(min(box_width, box_height) * 0.14))
    draw.rounded_rectangle(
        (0, 0, box_width - 1, box_height - 1),
        radius=radius,
        fill=background_fill,
    )

    logo_x = (box_width - logo.width) // 2
    logo_y = (box_height - logo.height) // 2
    logo_box.alpha_composite(logo, (logo_x, logo_y))

    final_x = (width - box_width) // 2
    final_y = (height - box_height) // 2
    qr_image.alpha_composite(logo_box, (final_x, final_y))

    return qr_image


# ============================================================
# BRANDING / OUTER PADDING
# ============================================================

def add_branding(
    qr_image,
    company_name: str,
    outer_padding: int,
    qr_color: str,
    background_color: str,
):
    width, height = qr_image.size
    outer_padding = int(outer_padding)

    title_height = 0
    if company_name:
        title_height = max(80, int(width * 0.14))

    final_width = width + (outer_padding * 2)
    final_height = height + (outer_padding * 2) + title_height

    result = Image.new(
        "RGBA",
        (final_width, final_height),
        hex_to_rgba(background_color, 255),
    )

    qr_x = outer_padding
    qr_y = outer_padding + title_height
    result.alpha_composite(qr_image, (qr_x, qr_y))

    if company_name:
        draw = ImageDraw.Draw(result)

        max_text_width = final_width - 30
        start_size = max(24, int(width * 0.08))
        font, _, bbox = get_fitting_font_and_size(
            company_name,
            max_text_width,
            start_size,
        )

        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        text_x = (final_width - text_width) // 2
        text_y = max(8, (title_height - text_height) // 2)

        draw.text(
            (text_x, text_y),
            company_name,
            fill=qr_color,
            font=font,
        )

    return result


# ============================================================
# EXPORT HELPERS
# ============================================================

def image_to_png(image):
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    return buffer.getvalue()


def create_pdf(image, dpi: int = 300):
    png_bytes = image_to_png(image.convert("RGBA"))
    image_buffer = io.BytesIO(png_bytes)

    width, height = image.size

    scale = 72 / dpi
    pdf_width = width * scale
    pdf_height = height * scale

    pdf_buffer = io.BytesIO()
    pdf = canvas.Canvas(
        pdf_buffer,
        pagesize=(pdf_width, pdf_height),
    )

    pdf.drawImage(
        ImageReader(image_buffer),
        0,
        0,
        width=pdf_width,
        height=pdf_height,
        mask="auto",
    )

    pdf.save()
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()


# ============================================================
# SVG HELPERS
# ============================================================

def is_in_finder_eye(row: int, col: int, size: int):
    in_top_left = row < 7 and col < 7
    in_top_right = row < 7 and col >= size - 7
    in_bottom_left = row >= size - 7 and col < 7
    return in_top_left or in_top_right or in_bottom_left


def svg_rect(x, y, width, height, fill, rx=0):
    if rx > 0:
        return (
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{width:.2f}" '
            f'height="{height:.2f}" rx="{rx:.2f}" ry="{rx:.2f}" '
            f'fill="{fill}" />'
        )
    return (
        f'<rect x="{x:.2f}" y="{y:.2f}" width="{width:.2f}" '
        f'height="{height:.2f}" fill="{fill}" />'
    )


def svg_circle(cx, cy, r, fill):
    return (
        f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" '
        f'fill="{fill}" />'
    )


def svg_module_element(x, y, module_size, style, color):
    if style == "Dots":
        return svg_circle(
            x + (module_size / 2),
            y + (module_size / 2),
            module_size * 0.34,
            color,
        )

    if style == "Rounded":
        return svg_rect(
            x,
            y,
            module_size,
            module_size,
            color,
            rx=module_size * 0.28,
        )

    return svg_rect(x, y, module_size, module_size, color)


def svg_eye_elements(x, y, module_size, style, color, background_color):
    elements = []

    outer = 7 * module_size
    middle = 5 * module_size
    inner = 3 * module_size

    if style == "Circle":
        cx = x + outer / 2
        cy = y + outer / 2

        elements.append(svg_circle(cx, cy, outer / 2, color))
        elements.append(svg_circle(cx, cy, middle / 2, background_color))
        elements.append(svg_circle(cx, cy, inner / 2, color))

    elif style == "Rounded":
        outer_rx = module_size * 1.35
        middle_rx = module_size * 1.0
        inner_rx = module_size * 0.8

        elements.append(svg_rect(x, y, outer, outer, color, rx=outer_rx))
        elements.append(
            svg_rect(
                x + module_size,
                y + module_size,
                middle,
                middle,
                background_color,
                rx=middle_rx,
            )
        )
        elements.append(
            svg_rect(
                x + 2 * module_size,
                y + 2 * module_size,
                inner,
                inner,
                color,
                rx=inner_rx,
            )
        )

    else:
        elements.append(svg_rect(x, y, outer, outer, color))
        elements.append(
            svg_rect(
                x + module_size,
                y + module_size,
                middle,
                middle,
                background_color,
            )
        )
        elements.append(
            svg_rect(
                x + 2 * module_size,
                y + 2 * module_size,
                inner,
                inner,
                color,
            )
        )

    return elements


def create_vector_svg(
    qr_obj,
    company_name: str,
    config: dict,
    logo_image=None,
):
    # Real vector QR geometry
    modules = qr_obj.modules
    module_count = len(modules)
    quiet_zone = qr_obj.border
    module_size = 20

    qr_render_size = (module_count + (quiet_zone * 2)) * module_size
    outer_padding = int(config["outer_padding"])
    title_height = max(80, int(qr_render_size * 0.14)) if company_name else 0

    final_width = qr_render_size + (outer_padding * 2)
    final_height = qr_render_size + (outer_padding * 2) + title_height

    qr_origin_x = outer_padding
    qr_origin_y = outer_padding + title_height

    qr_color = config["qr_color"]
    background_color = config["background_color"]
    module_style = config["module_style"]
    eye_style = config["eye_style"]
    logo_percentage = config["logo_percentage"]
    logo_background_mode = config["logo_background_mode"]

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{final_width}" height="{final_height}" '
            f'viewBox="0 0 {final_width} {final_height}" '
            f'role="img" aria-labelledby="title">'
        ),
        f'<title id="title">{html.escape(company_name or "Branded QR Code")}</title>',
        svg_rect(0, 0, final_width, final_height, background_color),
    ]

    if company_name:
        max_text_width = final_width - 30
        start_size = max(24, int(qr_render_size * 0.08))
        _, fitted_size, _ = get_fitting_font_and_size(
            company_name,
            max_text_width,
            start_size,
        )

        parts.append(
            f'<text x="{final_width / 2:.2f}" y="{title_height / 2:.2f}" '
            f'font-family="Arial, DejaVu Sans, Liberation Sans, sans-serif" '
            f'font-size="{fitted_size}" font-weight="700" fill="{qr_color}" '
            f'text-anchor="middle" dominant-baseline="middle">'
            f'{html.escape(company_name)}'
            f'</text>'
        )

    # Draw all non-finder modules
    for row_index, row in enumerate(modules):
        for col_index, value in enumerate(row):
            if not value:
                continue

            if is_in_finder_eye(row_index, col_index, module_count):
                continue

            x = qr_origin_x + (col_index + quiet_zone) * module_size
            y = qr_origin_y + (row_index + quiet_zone) * module_size

            parts.append(
                svg_module_element(
                    x,
                    y,
                    module_size,
                    module_style,
                    qr_color,
                )
            )

    # Draw the 3 finder eyes separately
    eye_positions = [
        (
            qr_origin_x + quiet_zone * module_size,
            qr_origin_y + quiet_zone * module_size,
        ),
        (
            qr_origin_x + (quiet_zone + module_count - 7) * module_size,
            qr_origin_y + quiet_zone * module_size,
        ),
        (
            qr_origin_x + quiet_zone * module_size,
            qr_origin_y + (quiet_zone + module_count - 7) * module_size,
        ),
    ]

    for eye_x, eye_y in eye_positions:
        parts.extend(
            svg_eye_elements(
                eye_x,
                eye_y,
                module_size,
                eye_style,
                qr_color,
                background_color,
            )
        )

    # Optional logo
    if logo_image is not None:
        safe_percentage = min(max(int(logo_percentage), 5), 25)
        target_size = int(qr_render_size * safe_percentage / 100)

        logo = logo_image.copy().convert("RGBA")
        logo.thumbnail((target_size, target_size), Image.Resampling.LANCZOS)

        logo_x = qr_origin_x + (qr_render_size - logo.width) / 2
        logo_y = qr_origin_y + (qr_render_size - logo.height) / 2

        background_fill = None
        if logo_background_mode == "White":
            background_fill = "#FFFFFF"
        elif logo_background_mode == "Same as QR background":
            background_fill = background_color

        if background_fill is not None:
            padding = max(12, int(target_size * 0.12))
            bg_width = logo.width + (padding * 2)
            bg_height = logo.height + (padding * 2)
            bg_x = qr_origin_x + (qr_render_size - bg_width) / 2
            bg_y = qr_origin_y + (qr_render_size - bg_height) / 2
            radius = max(10, int(min(bg_width, bg_height) * 0.14))

            parts.append(
                svg_rect(
                    bg_x,
                    bg_y,
                    bg_width,
                    bg_height,
                    background_fill,
                    rx=radius,
                )
            )

            logo_x = bg_x + (bg_width - logo.width) / 2
            logo_y = bg_y + (bg_height - logo.height) / 2

        logo_buffer = io.BytesIO()
        logo.save(logo_buffer, format="PNG")
        logo_encoded = base64.b64encode(logo_buffer.getvalue()).decode("utf-8")

        parts.append(
            f'<image href="data:image/png;base64,{logo_encoded}" '
            f'x="{logo_x:.2f}" y="{logo_y:.2f}" '
            f'width="{logo.width}" height="{logo.height}" '
            f'preserveAspectRatio="xMidYMid meet" />'
        )

    parts.append("</svg>")

    return "\n".join(parts).encode("utf-8")


# ============================================================
# SAFETY CHECK
# ============================================================

def safety_check(config: dict):
    warnings = []

    qr_color = config["qr_color"]
    background_color = config["background_color"]

    contrast = contrast_ratio(qr_color, background_color)

    qr_lum = relative_luminance(hex_to_rgb(qr_color))
    bg_lum = relative_luminance(hex_to_rgb(background_color))

    if contrast < 4.5:
        warnings.append(
            f"QR contrast is low ({contrast:.1f}:1). "
            "Use a darker QR color or lighter background."
        )

    if qr_lum >= bg_lum:
        warnings.append(
            "For maximum scan reliability, use a darker QR color "
            "on a lighter background."
        )

    return len(warnings) == 0, warnings, contrast


# ============================================================
# STATE HELPERS
# ============================================================

def build_signature(
    url,
    company_name,
    module_style,
    eye_style,
    qr_color,
    background_color,
    logo_percentage,
    logo_background_mode,
    outer_padding,
    has_logo,
):
    return {
        "url": url.strip(),
        "company_name": company_name.strip(),
        "module_style": module_style,
        "eye_style": eye_style,
        "qr_color": qr_color,
        "background_color": background_color,
        "logo_percentage": logo_percentage,
        "logo_background_mode": logo_background_mode,
        "outer_padding": outer_padding,
        "has_logo": has_logo,
    }


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🔳 Branded QR Generator</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">'
    "Create customized, logo-enabled QR codes for your company."
    "</div>",
    unsafe_allow_html=True,
)


# ============================================================
# LAYOUT
# ============================================================

left, right = st.columns([0.42, 0.58], gap="large")


# ============================================================
# LEFT PANEL
# ============================================================

with left:
    st.subheader("QR Configuration")

    url = st.text_input(
        "URL",
        placeholder="https://www.example.com",
        help="Enter the URL you want the QR code to open.",
    )

    company_name = st.text_input(
        "Company Name",
        placeholder="My Company",
    )

    logo_file = st.file_uploader(
        "Company Logo",
        type=["png", "jpg", "jpeg", "webp"],
        help="PNG with transparency is recommended.",
    )

    logo = None
    if logo_file:
        try:
            logo = Image.open(logo_file).convert("RGBA")
            st.image(
                logo,
                caption="Uploaded logo",
                width=120,
            )
        except Exception:
            st.error("Could not read the uploaded logo.")
            logo = None

    st.divider()

    module_style = st.selectbox(
        "QR Module Style",
        ["Square", "Rounded", "Dots"],
        index=0,
    )

    eye_style = st.selectbox(
        "Finder / Corner Style",
        ["Square", "Rounded", "Circle"],
        index=0,
    )

    st.divider()

    qr_color = st.color_picker(
        "QR Color",
        "#111111",
    )

    background_color = st.color_picker(
        "Background Color",
        "#FFFFFF",
    )

    logo_percentage = st.slider(
        "Logo Size",
        min_value=5,
        max_value=25,
        value=18,
        step=1,
        format="%d%%",
        help="Keep the logo relatively small for better scanning.",
    )

    logo_background_mode = st.selectbox(
        "Logo Background",
        ["White", "Same as QR background", "Transparent"],
        index=0,
        help="A background behind the logo usually improves scan reliability.",
    )

    outer_padding = st.slider(
        "Outer Padding",
        min_value=0,
        max_value=100,
        value=30,
        step=5,
        help="Controls the space around the QR and title area.",
    )

    st.divider()

    generate = st.button(
        "🚀 Generate QR Code",
        type="primary",
        use_container_width=True,
    )


# ============================================================
# GENERATION
# ============================================================

current_signature = build_signature(
    url=url,
    company_name=company_name,
    module_style=module_style,
    eye_style=eye_style,
    qr_color=qr_color,
    background_color=background_color,
    logo_percentage=logo_percentage,
    logo_background_mode=logo_background_mode,
    outer_padding=outer_padding,
    has_logo=logo is not None,
)

if generate:
    if not url.strip():
        st.error("Please enter a URL.")

    elif not validate_url(url):
        st.error("Please enter a valid URL beginning with http:// or https://")

    else:
        with st.spinner("Generating branded QR code..."):
            try:
                config = {
                    "qr_color": qr_color,
                    "background_color": background_color,
                    "module_style": module_style,
                    "eye_style": eye_style,
                    "logo_percentage": logo_percentage,
                    "logo_background_mode": logo_background_mode,
                    "outer_padding": outer_padding,
                }

                qr_obj = create_qr_object(url.strip())

                qr_image = generate_qr_image(
                    qr_obj=qr_obj,
                    qr_color=qr_color,
                    background_color=background_color,
                    module_style=module_style,
                )

                if logo is not None:
                    qr_image = add_logo(
                        qr_image=qr_image,
                        logo_image=logo,
                        logo_percentage=logo_percentage,
                        logo_background_mode=logo_background_mode,
                        background_color=background_color,
                    )

                branded_image = add_branding(
                    qr_image=qr_image,
                    company_name=company_name.strip(),
                    outer_padding=outer_padding,
                    qr_color=qr_color,
                    background_color=background_color,
                )

                st.session_state.generated_qr = {
                    "url": url.strip(),
                    "company_name": company_name.strip(),
                    "config": config,
                    "qr_obj": qr_obj,
                    "qr_image": branded_image,
                    "logo_image": logo.copy() if logo is not None else None,
                    "signature": current_signature,
                }

            except Exception as error:
                st.error(f"Could not generate QR code: {error}")


# ============================================================
# RIGHT PANEL
# ============================================================

with right:
    st.subheader("Preview")

    if "generated_qr" not in st.session_state:
        st.info(
            "Configure your QR code and click **Generate QR Code**."
        )

    else:
        saved = st.session_state.generated_qr

        if current_signature != saved["signature"]:
            st.info(
                "You changed some settings after the last generation. "
                "Click **Generate QR Code** again to refresh the preview."
            )

        qr_image = saved["qr_image"]
        saved_config = saved["config"]

        st.markdown(
            '<div class="preview-box">',
            unsafe_allow_html=True,
        )

        st.image(qr_image, width=500)

        st.markdown(
            "</div>",
            unsafe_allow_html=True,
        )

        st.write("")

        # ----------------------------------------------------
        # SAFETY
        # ----------------------------------------------------

        safe, warnings, contrast = safety_check(saved_config)

        if safe:
            st.markdown(
                f"""
                <div class="safety-good">
                    ✓ <b>Good QR settings</b><br>
                    Contrast: {contrast:.1f}:1
                    <br><br>
                    Always test the final QR with a phone
                    before printing or publishing.
                </div>
                """,
                unsafe_allow_html=True,
            )

        else:
            warning_text = "<br>".join(f"• {warning}" for warning in warnings)

            st.markdown(
                f"""
                <div class="safety-warning">
                    ⚠ <b>Review these settings</b><br>
                    {warning_text}
                    <br><br>
                    Test the QR with multiple phones before use.
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.write("")

        # ----------------------------------------------------
        # DOWNLOAD
        # ----------------------------------------------------

        st.subheader("Download")

        png_data = image_to_png(qr_image)

        svg_data = create_vector_svg(
            qr_obj=saved["qr_obj"],
            company_name=saved["company_name"],
            config=saved_config,
            logo_image=saved["logo_image"],
        )

        pdf_data = create_pdf(qr_image, dpi=300)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.download_button(
                "⬇ PNG",
                data=png_data,
                file_name="branded_qr.png",
                mime="image/png",
                use_container_width=True,
            )

        with col2:
            st.download_button(
                "⬇ SVG",
                data=svg_data,
                file_name="branded_qr.svg",
                mime="image/svg+xml",
                use_container_width=True,
            )

        with col3:
            st.download_button(
                "⬇ PDF",
                data=pdf_data,
                file_name="branded_qr.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

        st.caption(f"QR content: {saved['url']}")
        st.markdown(
            '<div class="small-note">SVG export uses true vector shapes for the QR geometry. '
            'If you upload a raster logo (PNG/JPG/WebP), that logo is embedded inside the SVG.</div>',
            unsafe_allow_html=True,
        )