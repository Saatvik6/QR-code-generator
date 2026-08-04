from io import BytesIO
from urllib.parse import urlparse

import qrcode
import qrcode.image.svg
import streamlit as st


st.set_page_config(
    page_title="Permanent QR Code Generator",
    page_icon="🔳",
    layout="centered",
)


def is_valid_url(url: str) -> bool:
    """Check whether the entered text is a valid HTTP or HTTPS URL."""
    parsed_url = urlparse(url)

    return (
        parsed_url.scheme in {"http", "https"}
        and bool(parsed_url.netloc)
    )


def generate_png(url: str) -> bytes:
    """Generate a PNG QR code and return it as bytes."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12,
        border=4,
    )

    qr.add_data(url)
    qr.make(fit=True)

    image = qr.make_image(
        fill_color="black",
        back_color="white",
    )

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)

    return buffer.getvalue()


def generate_svg(url: str) -> bytes:
    """Generate an SVG QR code and return it as bytes."""
    factory = qrcode.image.svg.SvgPathImage

    image = qrcode.make(
        url,
        image_factory=factory,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        border=4,
    )

    buffer = BytesIO()
    image.save(buffer)
    buffer.seek(0)

    return buffer.getvalue()


st.title("Permanent QR Code Generator")

st.write(
    "Enter a link to create a static QR code that can be "
    "downloaded and used on posters, forms, cards, and standees."
)

url = st.text_input(
    "Enter your link",
    placeholder="https://example.com",
)

generate_button = st.button(
    "Generate QR Code",
    type="primary",
    use_container_width=True,
)

if generate_button:
    cleaned_url = url.strip()

    if not cleaned_url:
        st.warning("Please enter a link.")

    elif not is_valid_url(cleaned_url):
        st.error(
            "Please enter a complete URL starting with "
            "`https://` or `http://`."
        )

    else:
        try:
            png_data = generate_png(cleaned_url)
            svg_data = generate_svg(cleaned_url)

            st.session_state["qr_url"] = cleaned_url
            st.session_state["png_data"] = png_data
            st.session_state["svg_data"] = svg_data

        except Exception as error:
            st.error(f"Could not generate the QR code: {error}")


if (
    "png_data" in st.session_state
    and "svg_data" in st.session_state
):
    st.success("Your QR code has been generated.")

    st.image(
        st.session_state["png_data"],
        caption="Scan this QR code to test it",
        width=350,
    )

    st.caption(
        f"Destination: {st.session_state['qr_url']}"
    )

    png_column, svg_column = st.columns(2)

    with png_column:
        st.download_button(
            label="Download PNG",
            data=st.session_state["png_data"],
            file_name="permanent_qr_code.png",
            mime="image/png",
            use_container_width=True,
        )

    with svg_column:
        st.download_button(
            label="Download SVG",
            data=st.session_state["svg_data"],
            file_name="permanent_qr_code.svg",
            mime="image/svg+xml",
            use_container_width=True,
        )

    st.info(
        "Use PNG for normal digital use. Use SVG for large-format "
        "printing because it can be resized without becoming blurry."
    )