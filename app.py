import io
import os
import platform
import re
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, request
from PIL import Image
import pytesseract

from db import get_connection, init_db, seed_sample_data
from models import EqualSplit, SplitFactory, SplitType

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

# Only set an explicit path on Windows (local dev). On Render's Linux
# container, Tesseract is installed via the Dockerfile and already on PATH,
# so pytesseract finds it automatically without this.
if platform.system() == 'Windows':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Users\riyam\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'


init_db()
seed_sample_data()


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


@app.route('/compute-summary', methods=['POST'])
def compute_summary():
    payload = request.get_json(silent=True) or {}
    items = payload.get('items', [])

    if not isinstance(items, list):
        return jsonify({'error': 'Expected an items array'}), 400

    # First pass: validate every item BEFORE calculating anything.
    # An item with nobody assigned should never silently vanish from the
    # totals -- that's data loss that looks like a correct response.
    unassigned_items = []
    invalid_items = []

    for item in items:
        name = item.get('name')
        price = item.get('price')
        assigned_to = item.get('assignedTo', [])

        if not name or price is None:
            invalid_items.append(item.get('name') or '(unnamed item)')
            continue

        if not isinstance(assigned_to, list) or not assigned_to:
            unassigned_items.append(name)

    if invalid_items:
        return jsonify({
            'error': 'Some items are missing a name or price.',
            'invalidItems': invalid_items,
        }), 400

    if unassigned_items:
        return jsonify({
            'error': 'Every item needs at least one person assigned before totals can be calculated.',
            'unassignedItems': unassigned_items,
        }), 400

    # Second pass: everything is valid, so it's now safe to calculate.
    totals: dict[str, float] = {}

    for item in items:
        name = item['name']
        price = item['price']
        assigned_to = item['assignedTo']
        split_type = item.get('splitType', SplitType.EQUAL)
        values = item.get('values') or item.get('percentages')

        strategy = SplitFactory.create_split_strategy(split_type)

        try:
            splits = strategy.calc_split(float(price), [str(person) for person in assigned_to], values)
        except ValueError as exc:
            return jsonify({'error': f'{name}: {exc}'}), 400

        for split in splits:
            totals[str(split.user_id)] = round(totals.get(str(split.user_id), 0.0) + float(split.amount), 2)

    return jsonify({'totals': totals})


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


@app.route('/groups', methods=['GET'])
def get_groups():
    conn = get_connection()
    try:
        groups = conn.execute("SELECT id, name FROM groups ORDER BY id").fetchall()
        payload = []
        for group in groups:
            members = conn.execute(
                "SELECT person_name FROM group_members WHERE group_id = ? ORDER BY person_name",
                (group["id"],),
            ).fetchall()
            payload.append({
                "id": group["id"],
                "name": group["name"],
                "members": [row["person_name"] for row in members],
            })
        return jsonify(payload)
    finally:
        conn.close()


@app.route('/groups/<int:group_id>', methods=['GET'])
def get_group(group_id):
    conn = get_connection()
    try:
        group_row = conn.execute("SELECT id, name FROM groups WHERE id = ?", (group_id,)).fetchone()
        if not group_row:
            return jsonify({"error": "Group not found"}), 404

        members = conn.execute(
            "SELECT person_name FROM group_members WHERE group_id = ? ORDER BY person_name",
            (group_id,),
        ).fetchall()
        return jsonify({
            "id": group_row["id"],
            "name": group_row["name"],
            "members": [row["person_name"] for row in members],
        })
    finally:
        conn.close()


@app.route('/groups/<int:group_id>/transactions', methods=['GET'])
def get_group_transactions(group_id):
    conn = get_connection()
    try:
        group_exists = conn.execute("SELECT 1 FROM groups WHERE id = ?", (group_id,)).fetchone()
        if not group_exists:
            return jsonify({"error": "Group not found"}), 404

        rows = conn.execute(
            """
            SELECT id, title, description, amount, paid_by, date, source
            FROM transactions
            WHERE group_id = ?
            ORDER BY date DESC, id DESC
            """,
            (group_id,),
        ).fetchall()

        transactions = []
        for row in rows:
            assignees = conn.execute(
                "SELECT person_name, amount FROM transaction_assignees WHERE transaction_id = ? ORDER BY person_name",
                (row["id"],),
            ).fetchall()
            items = conn.execute(
                "SELECT id, item_name, item_price FROM transaction_items WHERE transaction_id = ? ORDER BY id",
                (row["id"],),
            ).fetchall()

            item_payload = []
            for item in items:
                splits = conn.execute(
                    "SELECT person_name, amount FROM transaction_item_splits WHERE item_id = ? ORDER BY person_name",
                    (item["id"],),
                ).fetchall()
                item_payload.append({
                    "id": item["id"],
                    "name": item["item_name"],
                    "price": round(float(item["item_price"]), 2),
                    "splits": [
                        {"person": split["person_name"], "amount": round(float(split["amount"]), 2)}
                        for split in splits
                    ],
                })

            transactions.append({
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "amount": round(float(row["amount"]), 2),
                "paidBy": row["paid_by"],
                "date": row["date"],
                "source": row["source"],
                "assignees": [
                    {"person": assignee["person_name"], "amount": round(float(assignee["amount"]), 2)}
                    for assignee in assignees
                ],
                "items": item_payload,
            })

        return jsonify(transactions)
    finally:
        conn.close()


@app.route('/groups/<int:group_id>/transactions', methods=['POST'])
def create_transaction(group_id):
    payload = request.get_json(silent=True) or {}
    conn = get_connection()
    try:
        group_exists = conn.execute("SELECT 1 FROM groups WHERE id = ?", (group_id,)).fetchone()
        if not group_exists:
            return jsonify({"error": "Group not found"}), 404

        title = (payload.get("title") or "").strip()
        description = (payload.get("description") or "").strip()
        amount = payload.get("amount")
        paid_by = (payload.get("paidBy") or payload.get("paid_by") or "").strip()
        source = (payload.get("source") or "manual").strip().lower()
        assigned_to = payload.get("assignedTo") or []
        items = payload.get("items") or []
        date = payload.get("date") or _iso_now()

        if not title:
            return jsonify({"error": "Title is required"}), 400
        if amount is None:
            return jsonify({"error": "Amount is required"}), 400
        if not paid_by:
            return jsonify({"error": "Paid by is required"}), 400
        if source not in {"manual", "scan"}:
            return jsonify({"error": "Invalid source"}), 400

        if source == "manual":
            if not isinstance(assigned_to, list) or not assigned_to:
                return jsonify({"error": "At least one assignee is required"}), 400
            strategy = SplitFactory.create_split_strategy(SplitType.EQUAL)
            splits = strategy.calc_split(float(amount), [str(person) for person in assigned_to])
            if not splits:
                return jsonify({"error": "Could not compute splits"}), 400
        else:
            if not isinstance(items, list) or not items:
                return jsonify({"error": "At least one scanned item is required"}), 400
            unassigned_items = []
            for item in items:
                assigned_to = item.get("assignedTo") or []
                if not isinstance(assigned_to, list) or not assigned_to:
                    unassigned_items.append(item.get("name") or "(unnamed item)")
            if unassigned_items:
                return jsonify({
                    "error": "Every item needs at least one person assigned before the transaction can be saved.",
                    "unassignedItems": unassigned_items,
                }), 400

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO transactions (group_id, title, description, amount, paid_by, date, source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (group_id, title, description, float(amount), paid_by, date, source),
        )
        transaction_id = cursor.lastrowid

        if source == "manual":
            for split in splits:
                cursor.execute(
                    "INSERT INTO transaction_assignees (transaction_id, person_name, amount) VALUES (?, ?, ?)",
                    (transaction_id, split.user_id, float(split.amount)),
                )
        else:
            for item in items:
                item_name = (item.get("name") or "").strip()
                item_price = item.get("price")
                if not item_name or item_price is None:
                    continue

                cursor.execute(
                    "INSERT INTO transaction_items (transaction_id, item_name, item_price) VALUES (?, ?, ?)",
                    (transaction_id, item_name, float(item_price)),
                )
                item_id = cursor.lastrowid
                assigned_to = item.get("assignedTo") or []
                split_type = item.get("splitType", SplitType.EQUAL)
                values = item.get("values") or item.get("percentages")
                strategy = SplitFactory.create_split_strategy(split_type)
                item_splits = strategy.calc_split(float(item_price), [str(person) for person in assigned_to], values)
                for split in item_splits:
                    cursor.execute(
                        "INSERT INTO transaction_item_splits (item_id, person_name, amount) VALUES (?, ?, ?)",
                        (item_id, split.user_id, float(split.amount)),
                    )

        conn.commit()
        return jsonify({"id": transaction_id, "status": "created"}), 201
    finally:
        conn.close()


@app.route('/transactions/<int:transaction_id>', methods=['GET'])
def get_transaction(transaction_id):
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT id, group_id, title, description, amount, paid_by, date, source
            FROM transactions
            WHERE id = ?
            """,
            (transaction_id,),
        ).fetchone()
        if not row:
            return jsonify({"error": "Transaction not found"}), 404

        assignees = conn.execute(
            "SELECT person_name, amount FROM transaction_assignees WHERE transaction_id = ? ORDER BY person_name",
            (transaction_id,),
        ).fetchall()
        items = conn.execute(
            "SELECT id, item_name, item_price FROM transaction_items WHERE transaction_id = ? ORDER BY id",
            (transaction_id,),
        ).fetchall()

        item_payload = []
        for item in items:
            splits = conn.execute(
                "SELECT person_name, amount FROM transaction_item_splits WHERE item_id = ? ORDER BY person_name",
                (item["id"],),
            ).fetchall()
            item_payload.append({
                "id": item["id"],
                "name": item["item_name"],
                "price": round(float(item["item_price"]), 2),
                "splits": [
                    {"person": split["person_name"], "amount": round(float(split["amount"]), 2)}
                    for split in splits
                ],
            })

        return jsonify({
            "id": row["id"],
            "groupId": row["group_id"],
            "title": row["title"],
            "description": row["description"],
            "amount": round(float(row["amount"]), 2),
            "paidBy": row["paid_by"],
            "date": row["date"],
            "source": row["source"],
            "assignees": [
                {"person": assignee["person_name"], "amount": round(float(assignee["amount"]), 2)}
                for assignee in assignees
            ],
            "items": item_payload,
        })
    finally:
        conn.close()


@app.route('/transactions/<int:transaction_id>', methods=['PUT'])
def update_transaction(transaction_id):
    payload = request.get_json(silent=True) or {}
    conn = get_connection()
    try:
        transaction = conn.execute(
            "SELECT title, description, amount, source FROM transactions WHERE id = ?",
            (transaction_id,),
        ).fetchone()
        if not transaction:
            return jsonify({"error": "Transaction not found"}), 404
        if transaction["source"] != "manual":
            return jsonify({"error": "Only manual transactions can be edited"}), 400

        title = (payload.get("title") or "").strip()
        description = (payload.get("description") or "").strip()
        amount = payload.get("amount")
        assigned_to = payload.get("assignedTo") or []

        if not title:
            return jsonify({"error": "Title is required"}), 400
        if amount is None:
            return jsonify({"error": "Amount is required"}), 400
        if not isinstance(assigned_to, list) or not assigned_to:
            return jsonify({"error": "At least one assignee is required"}), 400

        try:
            amount = float(amount)
            strategy = SplitFactory.create_split_strategy(SplitType.EQUAL)
            splits = strategy.calc_split(amount, [str(person) for person in assigned_to])
        except (TypeError, ValueError) as exc:
            return jsonify({"error": str(exc) or "Amount must be a valid number"}), 400

        if not splits:
            return jsonify({"error": "Could not compute splits"}), 400

        conn.execute(
            "UPDATE transactions SET title = ?, description = ?, amount = ? WHERE id = ?",
            (title, description, amount, transaction_id),
        )
        conn.execute("DELETE FROM transaction_assignees WHERE transaction_id = ?", (transaction_id,))
        conn.executemany(
            "INSERT INTO transaction_assignees (transaction_id, person_name, amount) VALUES (?, ?, ?)",
            [(transaction_id, split.user_id, float(split.amount)) for split in splits],
        )
        conn.commit()
        return jsonify({"id": transaction_id, "status": "updated"})
    finally:
        conn.close()


@app.route('/groups/<int:group_id>/settle-up', methods=['POST'])
def settle_up(group_id):
    return jsonify({"status": "stubbed", "groupId": group_id})


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
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', debug=True, port=port)