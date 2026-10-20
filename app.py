import os
import sqlite3
from functools import wraps
from datetime import datetime
from flask import Flask, g, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("QUICKBITE_SECRET_KEY", "dev-only-change-this-secret")
DB_PATH = os.path.join(os.path.dirname(__file__), "quickbite.db")

RESTAURANTS = [
    {"id": 1, "name": "Spice Route", "cuisine": "Indian • Biryani", "rating": 4.5, "time": "25–35 min", "fee": 25, "image": "https://images.unsplash.com/photo-1565557623262-b51c2513a641?w=900"},
    {"id": 2, "name": "Pizza Corner", "cuisine": "Pizza • Italian", "rating": 4.3, "time": "20–30 min", "fee": 20, "image": "https://images.unsplash.com/photo-1513104890138-7c749659a591?w=900"},
    {"id": 3, "name": "Green Bowl", "cuisine": "Healthy • Salads", "rating": 4.4, "time": "15–25 min", "fee": 15, "image": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=900"},
    {"id": 4, "name": "Burger Station", "cuisine": "Burgers • Fast Food", "rating": 4.2, "time": "20–30 min", "fee": 20, "image": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=900"},
]
MENU = {
    1: [{"id": 101, "name": "Chicken Biryani", "price": 220, "veg": False}, {"id": 102, "name": "Paneer Biryani", "price": 180, "veg": True}, {"id": 103, "name": "Butter Naan", "price": 40, "veg": True}],
    2: [{"id": 201, "name": "Margherita Pizza", "price": 249, "veg": True}, {"id": 202, "name": "Farmhouse Pizza", "price": 329, "veg": True}, {"id": 203, "name": "Chicken Pizza", "price": 349, "veg": False}],
    3: [{"id": 301, "name": "Rainbow Salad", "price": 159, "veg": True}, {"id": 302, "name": "Grilled Paneer Bowl", "price": 199, "veg": True}],
    4: [{"id": 401, "name": "Classic Burger", "price": 149, "veg": False}, {"id": 402, "name": "Veggie Burger", "price": 129, "veg": True}, {"id": 403, "name": "French Fries", "price": 89, "veg": True}],
}
ORDER_STAGES = ["Order placed", "Restaurant is preparing your food", "Picked up by delivery partner", "Delivered"]

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(_error):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            items_json TEXT NOT NULL, total INTEGER NOT NULL, address TEXT NOT NULL,
            payment_method TEXT NOT NULL, payment_status TEXT NOT NULL,
            status_index INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id))""")
        # Demo admin: login with admin@quickbite.local / Admin123! after first run.
        cur = conn.execute("SELECT id FROM users WHERE email=?", ("admin@quickbite.local",))
        if not cur.fetchone():
            conn.execute("INSERT INTO users(name,email,password_hash,is_admin) VALUES(?,?,?,1)",
                         ("QuickBite Admin", "admin@quickbite.local", generate_password_hash("Admin123!")))
        conn.commit()

@app.before_request
def ensure_db():
    init_db()

def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return db().execute("SELECT id,name,email,is_admin FROM users WHERE id=?", (uid,)).fetchone()

@app.context_processor
def inject_user():
    return {"current_user": current_user(), "cart_count": sum(session.get("cart", {}).values())}

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper

def get_menu_item(item_id):
    for rid, items in MENU.items():
        for item in items:
            if item["id"] == item_id:
                restaurant = next(r for r in RESTAURANTS if r["id"] == rid)
                return item, restaurant
    return None, None

def cart_details():
    cart = session.get("cart", {})
    lines, subtotal = [], 0
    for item_id_text, qty in cart.items():
        try:
            item_id = int(item_id_text)
        except ValueError:
            continue
        item, restaurant = get_menu_item(item_id)
        if item and qty > 0:
            line_total = item["price"] * qty
            subtotal += line_total
            lines.append({"item": item, "restaurant": restaurant, "qty": qty, "line_total": line_total})
    return lines, subtotal

@app.route("/")
def index():
    query = request.args.get("q", "").strip().lower()
    restaurants = [r for r in RESTAURANTS if query in (r["name"] + " " + r["cuisine"]).lower()] if query else RESTAURANTS
    return render_template("index.html", restaurants=restaurants, query=query)

@app.route("/restaurant/<int:restaurant_id>")
def restaurant(restaurant_id):
    place = next((r for r in RESTAURANTS if r["id"] == restaurant_id), None)
    if not place:
        flash("Restaurant not found.", "warning")
        return redirect(url_for("index"))
    return render_template("restaurant.html", restaurant=place, menu=MENU[restaurant_id])

@app.post("/cart/add/<int:item_id>")
def add_to_cart(item_id):
    item, restaurant = get_menu_item(item_id)
    if not item:
        flash("That menu item could not be found.", "warning")
        return redirect(url_for("index"))
    cart = session.get("cart", {})
    # Keep a single restaurant in a cart, like many food ordering apps.
    for existing_id in list(cart.keys()):
        existing_item, existing_restaurant = get_menu_item(int(existing_id))
        if existing_item and existing_restaurant["id"] != restaurant["id"]:
            cart.pop(existing_id)
    key = str(item_id)
    cart[key] = cart.get(key, 0) + 1
    session["cart"] = cart
    flash(f"Added {item['name']} to your cart.", "success")
    return redirect(request.referrer or url_for("restaurant", restaurant_id=restaurant["id"]))

@app.route("/cart")
def cart():
    lines, subtotal = cart_details()
    delivery_fee = 25 if lines else 0
    return render_template("cart.html", lines=lines, subtotal=subtotal, delivery_fee=delivery_fee, total=subtotal+delivery_fee)

@app.post("/cart/update")
def update_cart():
    cart = session.get("cart", {})
    for item_id in list(cart.keys()):
        try:
            qty = int(request.form.get(f"qty_{item_id}", cart[item_id]))
        except (TypeError, ValueError):
            qty = cart[item_id]
        if qty <= 0:
            cart.pop(item_id, None)
        else:
            cart[item_id] = min(qty, 20)
    session["cart"] = cart
    return redirect(url_for("cart"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 8:
            flash("Enter your name, a valid email, and a password with at least 8 characters.", "warning")
            return render_template("register.html")
        try:
            cur = db().execute("INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",
                               (name, email, generate_password_hash(password)))
            db().commit()
            session.clear()
            session["user_id"] = cur.lastrowid
            session["cart"] = {}
            flash("Account created successfully.", "success")
            return redirect(url_for("index"))
        except sqlite3.IntegrityError:
            flash("An account with that email already exists.", "warning")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["cart"] = {}
            flash("Welcome back!", "success")
            next_url = request.args.get("next", "")
            return redirect(next_url if next_url.startswith("/") and not next_url.startswith("//") else url_for("index"))
        flash("Email or password is incorrect.", "warning")
    return render_template("login.html")

@app.post("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))

@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    lines, subtotal = cart_details()
    if not lines:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("index"))
    delivery_fee = 25
    total = subtotal + delivery_fee
    if request.method == "POST":
        address = request.form.get("address", "").strip()
        payment_method = request.form.get("payment_method", "cod")
        if len(address) < 10:
            flash("Please enter a complete delivery address.", "warning")
            return render_template("checkout.html", lines=lines, subtotal=subtotal, delivery_fee=delivery_fee, total=total)
        if payment_method not in ("cod", "demo"):
            flash("Choose a valid payment option.", "warning")
            return redirect(url_for("checkout"))
        # "demo" is only a simulated payment. Never mark a real payment paid from a browser form.
        payment_status = "pending" if payment_method == "cod" else "test_simulated"
        import json
        order_lines = [{"name": x["item"]["name"], "price": x["item"]["price"], "qty": x["qty"]} for x in lines]
        cur = db().execute("""INSERT INTO orders(user_id,items_json,total,address,payment_method,payment_status,status_index,created_at)
                              VALUES(?,?,?,?,?,?,0,?)""",
                           (current_user()["id"], json.dumps(order_lines), total, address, payment_method,
                            payment_status, datetime.utcnow().isoformat(timespec="seconds")))
        db().commit()
        session["cart"] = {}
        return redirect(url_for("order_detail", order_id=cur.lastrowid))
    return render_template("checkout.html", lines=lines, subtotal=subtotal, delivery_fee=delivery_fee, total=total)

@app.route("/orders")
@login_required
def orders():
    rows = db().execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC", (current_user()["id"],)).fetchall()
    return render_template("orders.html", orders=rows, stages=ORDER_STAGES)

@app.route("/order/<int:order_id>")
@login_required
def order_detail(order_id):
    order = db().execute("SELECT * FROM orders WHERE id=? AND user_id=?", (order_id, current_user()["id"])).fetchone()
    if not order:
        flash("Order not found.", "warning")
        return redirect(url_for("orders"))
    import json
    return render_template("order_detail.html", order=order, items=json.loads(order["items_json"]), stages=ORDER_STAGES)

@app.route("/api/order/<int:order_id>/status")
@login_required
def order_status(order_id):
    order = db().execute("SELECT id,status_index FROM orders WHERE id=? AND user_id=?", (order_id, current_user()["id"])).fetchone()
    if not order:
        return jsonify({"error": "not_found"}), 404
    return jsonify({"status": ORDER_STAGES[order["status_index"]], "status_index": order["status_index"]})

@app.route("/admin")
@login_required
def admin():
    if not current_user()["is_admin"]:
        flash("Admin access is required.", "warning")
        return redirect(url_for("index"))
    rows = db().execute("""SELECT orders.*, users.name AS customer_name FROM orders
                           JOIN users ON users.id=orders.user_id ORDER BY orders.id DESC""").fetchall()
    return render_template("admin.html", orders=rows, stages=ORDER_STAGES)

@app.post("/admin/order/<int:order_id>/status")
@login_required
def admin_update_status(order_id):
    if not current_user()["is_admin"]:
        return "Forbidden", 403
    try:
        status_index = int(request.form.get("status_index", 0))
    except ValueError:
        status_index = 0
    status_index = max(0, min(status_index, len(ORDER_STAGES)-1))
    db().execute("UPDATE orders SET status_index=? WHERE id=?", (status_index, order_id))
    db().commit()
    flash(f"Order #{order_id} updated.", "success")
    return redirect(url_for("admin"))

if __name__ == "__main__":
    app.run(debug=True)
