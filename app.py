import re

from flask import Flask, request, jsonify, render_template
import pytesseract
from PIL import Image
import io

app = Flask(__name__)

pytesseract.pytesseract.tesseract_cmd = r'C:\Users\riyam\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/scan', methods=['POST'])
def scan():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded', 'text': '', 'items': []}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No image uploaded', 'text': '', 'items': []}), 400

    try:
        image = Image.open(io.BytesIO(file.read()))
        text = pytesseract.image_to_string(image)
        items = parse_receipt(text)
        return jsonify({'text': text, 'items': items})
    except Exception as exc:
        return jsonify({'error': f'Failed to process image: {exc}', 'text': '', 'items': []}), 500


def parse_receipt(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    items = []
    skip_words = ['total', 'subtotal', 'tax', 'change', 'cash', 'visa', 'mastercard', 'balance', 'gratuity']

    for line in lines:
        lower_line = line.lower()
        if any(word in lower_line for word in skip_words):
            continue

        match = re.search(r'([0-9]+(?:\.[0-9]{1,2})?)\s*$', line)
        if not match:
            continue

        price = float(match.group(1))
        name = line[:match.start(1)].strip(' -:·')
        if not name:
            continue

        items.append({'name': name, 'price': round(price, 2)})

    return items


if __name__ == '__main__':
    app.run(debug=True)
