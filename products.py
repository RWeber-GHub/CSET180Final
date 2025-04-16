from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy import text
from db import engine

products_bp = Blueprint('products', __name__)

@products_bp.route('/create', methods=['GET', 'POST'])
def create_product():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        warranty = request.form['warranty']
        stock = request.form['stock']
        price = request.form['price']
        color_hexes = request.form.get('colors', '')
        selected_sizes = request.form.getlist('sizes')
        uploaded_images = request.files.getlist('images')

        with engine.begin() as conn:
            result = conn.execute(text("""
                INSERT INTO product (user_id, title, description, warranty, stock, price)
                VALUES (:uid, :title, :desc, :warranty, :stock, :price)
            """), {
                'uid': session.get('user_id'),  
                'title': title,
                'desc': description,
                'warranty': warranty or None,
                'stock': stock,
                'price': price
            })
            product_id = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()

            for hex_code in [c.strip() for c in color_hexes.split(',') if c.strip()]:
                color_result = conn.execute(text("INSERT INTO colors (color) VALUES (:color)"), {'color': hex_code})
                color_id = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                conn.execute(text("INSERT INTO product_colors (product_id, color_id) VALUES (:pid, :cid)"),
                             {'pid': product_id, 'cid': color_id})

            for size_id in selected_sizes:
                conn.execute(text("INSERT INTO product_sizes (product_id, size_id) VALUES (:pid, :sid)"),
                             {'pid': product_id, 'sid': size_id})

            for file in uploaded_images:
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    file_path = os.path.join('static/uploads', filename)
                    file.save(file_path)

                    conn.execute(text("INSERT INTO images (image) VALUES (:img)"), {'img': file_path})
                    image_id = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                    conn.execute(text("INSERT INTO product_images (product_id, image_id) VALUES (:pid, :imgid)"),
                                 {'pid': product_id, 'imgid': image_id})

        flash("Product created successfully.")
        return redirect(url_for('products.all_products'))

    with engine.connect() as conn:
        sizes = conn.execute(text("SELECT size_id, size FROM sizes")).fetchall()
    return render_template('create_product.html', sizes=sizes)


@products_bp.route('/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    with engine.connect() as conn:
        if request.method == 'POST':
            title = request.form['title']
            description = request.form['description']
            warranty = request.form['warranty']
            stock = request.form['stock']
            price = request.form['price']

            sql = text("""
                UPDATE product 
                SET title=:title, description=:desc, warranty=:warranty, stock=:stock, price=:price 
                WHERE product_id=:id
            """)
            conn.execute(sql, {
                'title': title,
                'desc': description,
                'warranty': warranty or None,
                'stock': stock,
                'price': price,
                'id': product_id
            })
            conn.commit()
            flash("Product updated.")
            return redirect(url_for('products.all_products'))

        result = conn.execute(text("SELECT * FROM product WHERE product_id=:id"), {'id': product_id}).fetchone()
        if result is None:
            flash("Product not found.")
            return redirect(url_for('index'))

    return render_template('edit_product.html', product=result)


@products_bp.route('/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM product WHERE product_id=:id"), {'id': product_id})
        conn.commit()

    flash("Product deleted.")
    return redirect(url_for('products.all_products'))


@products_bp.route('/all')
def all_products():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM product")).fetchall()

    return render_template('all_products.html', products=result)
