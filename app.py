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
    file = request.files['image']
    image = Image.open(io.BytesIO(file.read()))
    text = pytesseract.image_to_string(image)
    items = parse_receipt(text)
    return jsonify({'text': text, 'items': items})

def parse_receipt(text):
    lines = text.split('\n')
    items = []
    skip_words = ['total', 'subtotal', 'tax', 'change', 'cash', 'visa', 'mastercard']

    for line in lines:
        if any(word in line.lower() for word in skip_words):
            continue
        if re.search(r'\d+\.\d{2}', line):
            items.append(line.strip())

    return items

if __name__ == '__main__':
    app.run(debug=True)