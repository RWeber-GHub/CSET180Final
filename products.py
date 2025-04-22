from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from sqlalchemy import text
from db import engine
import os

products_bp = Blueprint('products', __name__, url_prefix='/products')
products_bp = Blueprint('products', __name__)


from collections import defaultdict


@products_bp.route('/')
def create():
    return render_template('create_products.html')

@products_bp.route('/create', methods=['GET', 'POST'])
def create_product():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        warranty = request.form['warranty']
        uploaded_images = request.files.getlist('images')

        variant_data = defaultdict(dict)
        for key, value in request.form.items():
            if key.startswith('variants'):
                parts = key.split('[')
                idx = parts[1][:-1]
                field = parts[2][:-1]
                variant_data[idx][field] = value

        variants = list(variant_data.values())

        UPLOAD_FOLDER = os.path.join('static', 'uploads')
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        with engine.begin() as conn:

            size_rows = conn.execute(text("SELECT size_id, size FROM sizes")).fetchall()
            size_map = {row.size.upper(): row.size_id for row in size_rows}

            total_stock = sum(int(v['stock']) for v in variants)
            base_price = float(variants[0]['price'])

            result = conn.execute(text("""
                INSERT INTO product (user_id, title, description, warranty, stock, price)
                VALUES (:uid, :title, :desc, :warranty, :stock, :price)
            """), {
                'uid': session.get('user_id'),
                'title': title,
                'desc': description,
                'warranty': warranty or None,
                'stock': total_stock,
                'price': base_price
            })
            product_id = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()

            used_color_ids = set()
            used_size_ids = set()

            for variant in variants:
                color = variant['color'].strip()
                size = variant['size'].strip().upper()
                stock = int(variant['stock'])
                price = float(variant['price'])

                conn.execute(text("""
                    INSERT INTO colors (color)
                    VALUES (:color)
                    ON DUPLICATE KEY UPDATE color_id = LAST_INSERT_ID(color_id)
                """), {'color': color})
                color_id = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                used_color_ids.add(color_id)

                size_id = size_map.get(size)
                if not size_id:
                    flash(f"Size '{size}' does not exist. Please create it first.")
                    return redirect(url_for('products.create_product'))
                used_size_ids.add(size_id)

                conn.execute(text("""
                    INSERT INTO product_variants (product_id, color_id, size_id, variant_stock, price)
                    VALUES (:pid, :cid, :sid, :stock, :price)
                """), {
                    'pid': product_id,
                    'cid': color_id,
                    'sid': size_id,
                    'stock': stock,
                    'price': price
                })

            for cid in used_color_ids:
                conn.execute(text("""
                    INSERT INTO product_colors (product_id, color_id)
                    VALUES (:pid, :cid)
                """), {'pid': product_id, 'cid': cid})

            for sid in used_size_ids:
                conn.execute(text("""
                    INSERT INTO product_sizes (product_id, size_id)
                    VALUES (:pid, :sid)
                """), {'pid': product_id, 'sid': sid})

            for file in uploaded_images:
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(file_path)

                    relative_path = os.path.join('static', 'uploads', filename)
                    conn.execute(text("INSERT INTO images (image) VALUES (:img)"), {'img': relative_path})
                    image_id = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                    conn.execute(text("INSERT INTO product_images (product_id, image_id) VALUES (:pid, :imgid)"),
                                 {'pid': product_id, 'imgid': image_id})

        flash("Product created successfully with variants.")
        return redirect(url_for('products.all_products'))

    with engine.connect() as conn:
        sizes = conn.execute(text("SELECT size_id, size FROM sizes")).fetchall()
    return render_template('all_products.html', sizes=sizes)


@products_bp.route('/gallery')
def product_gallery():
    with engine.connect() as conn:
        results = conn.execute(text("""
            SELECT 
                p.product_id, p.title, p.description, p.price, p.stock, p.warranty,
                GROUP_CONCAT(DISTINCT i.image) AS images,
                GROUP_CONCAT(DISTINCT c.color) AS colors,
                GROUP_CONCAT(DISTINCT s.size) AS sizes
            FROM product p
            LEFT JOIN product_images pi ON p.product_id = pi.product_id
            LEFT JOIN images i ON pi.image_id = i.image_id
            LEFT JOIN product_colors pc ON p.product_id = pc.product_id
            LEFT JOIN colors c ON pc.color_id = c.color_id
            LEFT JOIN product_sizes ps ON p.product_id = ps.product_id
            LEFT JOIN sizes s ON ps.size_id = s.size_id
            GROUP BY p.product_id
        """)).fetchall()

    products = []
    for row in results:
        products.append({
            'product_id': row.product_id,
            'title': row.title,
            'description': row.description,
            'price': row.price,
            'stock': row.stock,
            'warranty': row.warranty,
            'images': row.images.split(',') if row.images else [],
            'colors': row.colors.split(',') if row.colors else [],
            'sizes': row.sizes.split(',') if row.sizes else []
        })

    return render_template('all_products.html', products=products)






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
