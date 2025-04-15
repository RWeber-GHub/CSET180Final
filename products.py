from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from sqlalchemy import text
from db import engine, conn


products_bp = Blueprint('products', __name__)

def is_vendor_or_admin():
    return 'user_type' in session and session['user_type'] in ['B', 'C']

@products_bp.route('/create', methods=['GET', 'POST'])
def create_product():
    if not is_vendor_or_admin():
        flash("Unauthorized access.")
        return redirect(url_for('index'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        warranty = request.form['warranty']
        stock = request.form['stock']
        price = request.form['price']

        with engine.connect() as conn:
            sql = text("""
                INSERT INTO product (title, description, warranty, stock, price)
                VALUES (:title, :desc, :warranty, :stock, :price)
            """)
            conn.execute(sql, {
                'title': title,
                'desc': description,
                'warranty': warranty or None,
                'stock': stock,
                'price': price
            })
            conn.commit()
        flash("Product created.")
        return redirect(url_for('products.create_product'))

    return render_template('create_product.html')


@products_bp.route('/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if not is_vendor_or_admin():
        flash("Unauthorized access.")
        return redirect(url_for('index'))

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
            return redirect(url_for('products.edit_product', product_id=product_id))

        result = conn.execute(text("SELECT * FROM product WHERE product_id=:id"), {'id': product_id}).fetchone()
        if result is None:
            flash("Product not found.")
            return redirect(url_for('index'))

    return render_template('edit_product.html', product=result)


@products_bp.route('/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if not is_vendor_or_admin():
        flash("Unauthorized access.")
        return redirect(url_for('index'))

    with engine.connect() as conn:
        conn.execute(text("DELETE FROM product WHERE product_id=:id"), {'id': product_id})
        conn.commit()

    flash("Product deleted.")
    return redirect(url_for('create_products.html')) 
