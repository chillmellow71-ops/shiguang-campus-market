from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from pathlib import Path

app = Flask(__name__)
app.secret_key = "campus-market-demo"
# 将此地址替换为学校官方统一身份认证地址；登录在学校官网完成。
app.config["AUTH_URL"] = "https://uia.njfu.edu.cn/"

@app.context_processor
def inject_image_version():
    return {"image_version": int(Path(__file__).stat().st_mtime)}
DB_PATH = Path(__file__).with_name("market.db")
UPLOAD_DIR = Path(__file__).parent / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT,
            contact TEXT NOT NULL,
            image TEXT DEFAULT 'https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=800'
        )
    """)
    if conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        demo = [
            ("高等数学教材（同济版）", "教材", 18, "九成新，重点内容有少量笔记。", "李同学 13800001111", "/static/products/math.png"),
            ("无线蓝牙耳机", "数码", 69, "使用半年，功能正常，支持当面验货。", "王同学 13900002222", "/static/products/earphones.png"),
            ("宿舍收纳置物架", "生活用品", 25, "搬宿舍闲置，结实耐用。", "陈同学 13700003333", "/static/products/storage.png"),
            ("机械键盘", "数码", 99, "87键青轴，适合学习和编程。", "赵同学 13600004444", "/static/products/keyboard.jpg"),
        ]
        conn.executemany("INSERT INTO products(title,category,price,description,contact,image) VALUES(?,?,?,?,?,?)", demo)
    conn.commit()
    conn.close()


@app.route("/")
def index():
    keyword = request.args.get("keyword", "").strip()
    category = request.args.get("category", "全部")
    conn = get_db()
    sql = "SELECT * FROM products WHERE 1=1"
    params = []
    if keyword:
        sql += " AND (title LIKE ? OR description LIKE ?)"
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    if category and category != "全部":
        sql += " AND category = ?"
        params.append(category)
    sql += " ORDER BY id DESC"
    products = conn.execute(sql, params).fetchall()
    categories = [row[0] for row in conn.execute("SELECT DISTINCT category FROM products ORDER BY category").fetchall()]
    conn.close()
    return render_template("index.html", products=products, categories=categories, keyword=keyword, category=category)


@app.route("/publish", methods=["GET", "POST"])
def publish():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        price = request.form.get("price", "").strip()
        description = request.form.get("description", "").strip()
        contact = request.form.get("contact", "").strip()
        image_file = request.files.get("image")
        image = "/static/products/math.png"
        if image_file and image_file.filename:
            safe_name = Path(image_file.filename).name.replace(" ", "_")
            image_file.save(UPLOAD_DIR / safe_name)
            image = "/static/uploads/" + safe_name
        if not all([title, category, price, contact]):
            flash("请填写商品名称、分类、价格和联系方式。", "error")
            return render_template("publish.html")
        try:
            price_value = float(price)
        except ValueError:
            flash("价格必须是数字。", "error")
            return render_template("publish.html")
        conn = get_db()
        conn.execute("INSERT INTO products(title,category,price,description,contact,image) VALUES(?,?,?,?,?,?)", (title, category, price_value, description, contact, image))
        conn.commit()
        conn.close()
        flash("商品发布成功！", "success")
        return redirect(url_for("index"))
    return render_template("publish.html")

@app.route("/product/<int:product_id>")
def product_detail(product_id):
    conn = get_db(); product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone(); conn.close()
    if product is None:
        flash("商品不存在或已下架。", "error"); return redirect(url_for("index"))
    return render_template("detail.html", product=product)

@app.route("/product/<int:product_id>/buy", methods=["POST"])
def buy_product(product_id):
    conn = get_db(); product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone(); conn.close()
    if product is None:
        flash("商品不存在或已下架。", "error"); return redirect(url_for("index"))
    flash(f"已提交购买意向！请通过支付宝账号 {product['contact'].split()[-1]} 与卖家确认交易。", "success")
    return redirect(url_for("product_detail", product_id=product_id))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)



