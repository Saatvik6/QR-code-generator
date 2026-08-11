# Branded QR Generator

A Streamlit-powered web app for creating customizable branded QR codes with logo, style, and export options.

## Features

- Generate QR codes from any `http://` or `https://` URL
- Choose QR module style: `Square`, `Rounded`, or `Dots`
- Choose finder/corner style: `Square`, `Rounded`, or `Circle`
- Customize QR color and background color with color pickers
- Upload a company logo and place it at the center of the QR
- Add an optional title/company name above the QR
- Control logo size, logo background, and outer padding
- Export the result as `PNG`, `SVG`, or `PDF`
- Built-in contrast and safety warnings for better scan reliability

## Requirements

- Python 3.8+
- Dependencies listed in `requirements.txt`

## Installation

1. Clone or download the repository.
2. Create and activate a Python virtual environment.
3. Install dependencies:

```powershell
pip install -r requirements.txt
```

## Run locally

From the project root:

```powershell
python -m streamlit run app.py
```

Then open the local Streamlit URL shown in the terminal.

## Usage

1. Enter the destination URL in the `URL` field.
2. Optional: enter a company name for a branded title.
3. Upload a logo image (`PNG`, `JPG`, `JPEG`, or `WEBP`).
4. Customize QR style, finder style, colors, logo size, logo background, and padding.
5. Click **Generate QR Code**.
6. Download the final design as PNG, SVG, or PDF.

## Notes

- Use a darker QR color on a lighter background for best scanning results.
- Keep the logo size small enough to avoid interfering with QR readability.
- The app validates URLs and provides warnings when color contrast is too low.

## Dependencies

- `streamlit`
- `qrcode[pil]==8.2`
- `reportlab`
- `Pillow`

## Project files

- `app.py` — main Streamlit application
- `requirements.txt` — Python dependencies
- `README.md` — project documentation
