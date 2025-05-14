from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from sqlalchemy import text
from db import engine, conn
from datetime import date, datetime
import os
import json
import re

products_bp = Blueprint('products', __name__, url_prefix='/products')


from collections import defaultdict



@products_bp.route('/')
def create():
    return render_template('create_products.html')


@products_bp.route('/create', methods=['GET', 'POST'])
def create_product():
    if request.method == 'POST':
        try:
            print("\n=== FORM DATA ===")
            print(request.form.to_dict())
            print("\n=== FILES ===")
            print([f.filename for f in request.files.getlist('images')])

            title = request.form['title']
            description = request.form['description']
            warranty = request.form.get('warranty')
            category = request.form.get('category', 'Misc.')
            uploaded_images = request.files.getlist('images')

            variant_data = defaultdict(dict)
            for key, value in request.form.items():
                if key.startswith('variants['):
                    # Parse format: variants[0][color]
                    parts = key.split('[')
                    if len(parts) == 3:
                        idx = parts[1].rstrip(']')
                        field = parts[2].rstrip(']')
                        variant_data[idx][field] = value

            variants = list(variant_data.values())
            print("\n=== PARSED VARIANTS ===")
            print(variants)

            if not variants:
                flash("At least one variant is required", 'error')
                return redirect(url_for('products.create_product'))

            UPLOAD_FOLDER = os.path.join('static', 'uploads')
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)

            with engine.begin() as conn:
                size_rows = conn.execute(text("SELECT size_id, size FROM sizes")).fetchall()
                size_map = {row.size.upper(): row.size_id for row in size_rows}
                print("\n=== EXISTING SIZES ===")
                print(size_map)

                total_stock = sum(int(v.get('stock', 0)) for v in variants)
                base_price = float(variants[0].get('price', 0))

                conn.execute(text("""
                    INSERT INTO product 
                    (user_id, title, description, warranty, stock, price, category)
                    VALUES (:uid, :title, :desc, :warranty, :stock, :price, :category)
                """), {
                    'uid': session.get('user_id'),
                    'title': title,
                    'desc': description,
                    'warranty': warranty if warranty else None,
                    'stock': total_stock,
                    'price': base_price,
                    'category': category
                })
                product_id = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                print("\n=== CREATED PRODUCT ID ===")
                print(product_id)

                used_color_ids = set()
                used_size_ids = set()

                for variant in variants:
                    color = variant.get('color', '').strip()
                    size = variant.get('size', '').strip().upper()
                    stock = int(variant.get('stock', 0))
                    price = float(variant.get('price', 0))

                    if not color or not size:
                        flash("Color and size are required for each variant", 'error')
                        continue

                    conn.execute(text("""
                        INSERT INTO colors (color) VALUES (:color)
                        ON DUPLICATE KEY UPDATE color_id=LAST_INSERT_ID(color_id)
                    """), {'color': color})
                    color_id = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                    used_color_ids.add(color_id)

                    if size not in size_map:
                        conn.execute(text("INSERT INTO sizes (size) VALUES (:size)"), {'size': size})
                        size_id = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                        size_map[size] = size_id
                        print(f"Created new size: {size} (ID: {size_id})")
                    else:
                        size_id = size_map[size]
                    used_size_ids.add(size_id)

                    conn.execute(text("""
                        INSERT INTO product_variants
                        (product_id, color_id, size_id, variant_stock, price)
                        VALUES (:pid, :cid, :sid, :stock, :price)
                    """), {
                        'pid': product_id,
                        'cid': color_id,
                        'sid': size_id,
                        'stock': stock,
                        'price': price
                    })

                for color_id in used_color_ids:
                    conn.execute(text("""
                        INSERT IGNORE INTO product_colors (product_id, color_id)
                        VALUES (:pid, :cid)
                    """), {'pid': product_id, 'cid': color_id})

                for size_id in used_size_ids:
                    conn.execute(text("""
                        INSERT IGNORE INTO product_sizes (product_id, size_id)
                        VALUES (:pid, :sid)
                    """), {'pid': product_id, 'sid': size_id})

                for file in uploaded_images:
                    if file and file.filename:
                        filename = secure_filename(file.filename)
                        filepath = os.path.join(UPLOAD_FOLDER, filename)
                        file.save(filepath)

                        db_image_path = os.path.join('uploads', filename)
                        conn.execute(text("""
                            INSERT INTO images (image) VALUES (:path)
                        """), {'path': db_image_path})
                        image_id = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                        
                        conn.execute(text("""
                            INSERT INTO product_images (product_id, image_id)
                            VALUES (:pid, :imgid)
                        """), {'pid': product_id, 'imgid': image_id})

            flash("Product created successfully!", 'success')
            return redirect(url_for('products.product_gallery'))

        except Exception as e:
            print("\n=== ERROR ===")
            print(traceback.format_exc())
            flash(f"Error creating product: {str(e)}", 'error')
            return redirect(url_for('products.create_product'))

    with engine.connect() as conn:
        sizes = conn.execute(text("SELECT size_id, size FROM sizes")).fetchall()
    return render_template('all_products.html', sizes=sizes)
    


@products_bp.route('/gallery')
def product_gallery():
    user_id = session.get('user_id')
    user_type = session.get('user_type')
    today = date.today()

    with engine.connect() as conn:
        variant_query = text("""
            SELECT 
                pv.product_id,
                c.color, c.color_id,
                s.size, s.size_id,
                pv.variant_stock,
                pv.price
            FROM product_variants pv
            JOIN colors c ON pv.color_id = c.color_id
            JOIN sizes s ON pv.size_id = s.size_id
        """)
        variant_results = conn.execute(variant_query)
        
        discount_query = text("""
            SELECT product_id, discount_amount, discount_start, discount_end
            FROM discounts
        """)
        discount_results = conn.execute(discount_query)

        base_query = """
            SELECT 
                p.product_id, p.title, p.description, p.price, p.stock, p.warranty, p.user_id,
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
        """

        if user_type == 'B':  
            query = text(base_query + " WHERE p.user_id = :user_id GROUP BY p.product_id")
            results = conn.execute(query, {'user_id': user_id})
        else:  
            query = text(base_query + " GROUP BY p.product_id")
            results = conn.execute(query)

        def row_to_dict(row):
            return {key: value for key, value in row._mapping.items()}

        product_variants_map = {}
        for row in variant_results:
            row_dict = row_to_dict(row)
            pid = row_dict['product_id']
            variant = {
                'color': row_dict['color'],
                'color_id': row_dict['color_id'],
                'size': row_dict['size'],
                'size_id': row_dict['size_id'],
                'stock': row_dict['variant_stock'],
                'price': float(row_dict['price']) if row_dict['price'] is not None else None
            }
            if variant['price'] is not None:
                product_variants_map.setdefault(pid, []).append(variant)

        discounts_map = {}
        for row in discount_results:
            row_dict = row_to_dict(row)
            try:
                discount_start = (row_dict['discount_start'] 
                                 if isinstance(row_dict['discount_start'], date) 
                                 else datetime.strptime(str(row_dict['discount_start']), '%Y-%m-%d').date())
                discount_end = (row_dict['discount_end'] 
                               if isinstance(row_dict['discount_end'], date) 
                               else datetime.strptime(str(row_dict['discount_end']), '%Y-%m-%d').date())
                
                d = {
                    'discount_amount': row_dict['discount_amount'],
                    'discount_start': discount_start,
                    'discount_end': discount_end
                }
                discounts_map.setdefault(row_dict['product_id'], []).append(d)
            except Exception as e:
                print(f"Error processing discount for product {row_dict['product_id']}: {e}")
                continue

        products = []
        for row in results:
            row_dict = row_to_dict(row)
            product_id = row_dict['product_id']
            variants = product_variants_map.get(product_id, [])
            
            unique_sizes = list({v['size'] for v in variants})
            unique_colors = list({v['color'] for v in variants})
            
            active_discount = None
            for discount in discounts_map.get(product_id, []):
                if discount['discount_start'] <= today <= discount['discount_end']:
                    active_discount = discount
                    break
            
            products.append({
                'product_id': product_id,
                'title': row_dict['title'],
                'description': row_dict['description'],
                'price': float(row_dict['price']) if row_dict['price'] is not None else 0,
                'stock': row_dict['stock'],
                'warranty': row_dict['warranty'],
                'images': row_dict['images'].split(',') if row_dict['images'] else [],
                'colors': unique_colors, 
                'sizes': unique_sizes,    
                'variants': variants,
                'discount': active_discount,
                'variants_json': json.dumps(variants),
                'is_owner': (user_type == 'C') or (user_type == 'B' and row_dict['user_id'] == user_id)
            })

    return render_template('all_products.html', 
                         products=products, 
                         user_type=user_type)

@products_bp.route('/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    with engine.begin() as conn:
        if request.method == 'POST':
            title = request.form['title']
            description = request.form['description']
            warranty = request.form['warranty']
            conn.execute(text("""
                UPDATE product
                SET title = :title, description = :description, warranty = :warranty
                WHERE product_id = :pid
            """), {
                'title': title,
                'description': description,
                'warranty': warranty or None,
                'pid': product_id
            })

            flash('Product updated successfully.')
            return redirect(url_for('products.product_gallery'))

        product = conn.execute(text("""
            SELECT * FROM product WHERE product_id = :pid
        """), {'pid': product_id}).mappings().first()

        variants = conn.execute(text("""
            SELECT pv.variant_id, c.color, s.size, pv.variant_stock, pv.price
            FROM product_variants pv
            JOIN colors c ON pv.color_id = c.color_id
            JOIN sizes s ON pv.size_id = s.size_id
            WHERE pv.product_id = :pid
        """), {'pid': product_id}).mappings().all()

        return render_template('edit_product.html', product=product, variants=variants)

@products_bp.route('/update_variant/<int:variant_id>', methods=['POST'])
def update_variant(variant_id):
    color = request.form['color'].strip()
    size = request.form['size'].strip().upper()
    stock = int(request.form['stock'])
    price = float(request.form['price'])

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO colors (color) VALUES (:color)
            ON DUPLICATE KEY UPDATE color_id = LAST_INSERT_ID(color_id)
        """), {'color': color})
        color_id = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()

        size_row = conn.execute(text("SELECT size_id FROM sizes WHERE size = :size"), {'size': size}).first()
        if not size_row:
            flash(f"Size '{size}' not found.")
            return redirect(request.referrer)
        size_id = size_row.size_id

        conn.execute(text("""
            UPDATE product_variants
            SET color_id = :cid, size_id = :sid, variant_stock = :stock, price = :price
            WHERE variant_id = :vid
        """), {
            'cid': color_id,
            'sid': size_id,
            'stock': stock,
            'price': price,
            'vid': variant_id
        })

    flash("Variant updated.")
    return redirect(request.referrer)


@products_bp.route('/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                DELETE FROM product_images 
                WHERE product_id = :pid
            """), {'pid': product_id})
            
            conn.execute(text("""
                DELETE FROM product_variants 
                WHERE product_id = :pid
            """), {'pid': product_id})

            conn.execute(text("""
                DELETE FROM product 
                WHERE product_id = :pid
            """), {'pid': product_id})
            
        flash('Product deleted successfully', 'success')
        return redirect(url_for('products.product_gallery'))
    
    except Exception as e:
        flash(f'Error deleting product: {str(e)}', 'error')
        return redirect(url_for('products.product_gallery'))


@products_bp.route('/add_discount/<int:product_id>', methods=['POST'])
def add_discount(product_id):
    try:

        if not all(key in request.form for key in ['discount_amount', 'discount_start', 'discount_end']):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        try:
            amount = int(request.form['discount_amount'])
            if not (1 <= amount <= 100):
                raise ValueError
        except ValueError:
            return jsonify({'success': False, 'message': 'Discount must be 1-100%'}), 400

        start_date = request.form['discount_start']
        end_date = request.form['discount_end']

        if start_date > end_date:
            return jsonify({'success': False, 'message': 'End date must be after start date'}), 400

        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO discounts 
                (product_id, discount_amount, discount_start, discount_end)
                VALUES (:pid, :amount, :start, :end)
            """), {
                'pid': product_id,
                'amount': amount,
                'start': start_date,
                'end': end_date
            })

        return jsonify({'success': True, 'message': 'Discount added successfully'})

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e) if not isinstance(e, HTTPException) else e.description
        }), 400
    
