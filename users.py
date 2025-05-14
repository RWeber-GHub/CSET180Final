from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from sqlalchemy import create_engine, text
import bcrypt
from db import engine, conn
from datetime import date, datetime
import os
from werkzeug.utils import secure_filename

user_bp = Blueprint("user", __name__, static_folder="static", template_folder="templates")

@user_bp.route('/')
def user():
    user_id = session['user_id']
    user_type = session['user_type']
    user = conn.execute(text("""
        select * from user where user_id = :user_id
    """), {
        'user_id': user_id
    }).fetchone()
    return render_template('userview.html', user=user, user_type=user_type)

@user_bp.route('/address')
def address():
    user_id = session['user_id']
    addresses = []
    try:
        address_ids = conn.execute(text("""
        select address_id from user_address where user_id = :user_id
        """), {
        'user_id': user_id
        }).fetchall()
        print(f'{address_ids}HHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH')
        for address_id in address_ids:
            address = conn.execute(text("""
                select * from address where address_id = :address_id
            """), {
                'address_id': address_id[0]
            }).fetchone()
            default_address = conn.execute(text("""
                select default_address from user_address where address_id = :address_id
            """), {
                'address_id': address_id[0]
            }).fetchone()
            addresses.append({
                'address_id': address[0],
                'receiver': address[1],
                'contact_num': address[2],
                'street_num': address[3],
                'street_name': address[4],
                'unit_num': address[5],
                'unit_name': address[6],
                'city': address[7],
                'state': address[8],
                'zipcode': address[9],
                'default_address': default_address
            })
            
    except Exception as e:
        return render_template('address.html', addresses=addresses, error=str(e))
    return render_template('address.html', addresses=addresses)



@user_bp.route('/assign_address', methods=['POST', 'GET'])
def assign_address():
    user_id = session['user_id']
    receiver = request.form.get('receiver')
    phonenumber = request.form.get('phonenumber')
    street_number = request.form.get('street_number')
    street_name = request.form.get('street_name')
    unit_number = request.form.get('unit_number')
    unit_name = request.form.get('unit_name')
    city = request.form.get('city')
    state = request.form.get('state')
    zipcode = request.form.get('zipcode')
    conn.execute(text("""
        insert into address (receiver, contact_num, street_num, street_name, unit_num, unit_name, city, state, zipcode)
        values (:receiver, :contact_num, :street_num, :street_name, :unit_num, :unit_name, :city, :state, :zipcode)
    """), {
        'receiver': receiver,
        'contact_num': phonenumber,
        'street_num': street_number,
        'street_name': street_name,
        'unit_num': unit_number,
        'unit_name': unit_name, 
        'city': city,
        'state': state,
        'zipcode': zipcode
    })
    conn.commit()
    address_id = conn.execute(text("""
        select address_id from address where street_num = :street_num
    """), {
        'street_num': street_number
    }).fetchone()
    conn.execute(text("""
        insert into user_address (address_id, user_id, default_address)
        values (:address_id, :user_id, :default_address)
    """),{
        'address_id': address_id[0],
        'user_id': user_id,
        'default_address': 0
    })
    conn.commit()
    return redirect(url_for('user.address'))

@user_bp.route('/default_address', methods=['POST', 'GET'])
def default_address():
    user_id = session['user_id']
    address_id = request.form.get('address_id')

    conn.execute(text("""
        update user_address set default_address = 0 where default_address = 1
    """))
    conn.commit()
    conn.execute(text("""
        update user_address set default_address = 1 where address_id = :address_id
    """), {
        'address_id': address_id
    })
    conn.commit()
    return redirect(url_for('user.address'))

@user_bp.route('/chat')
def chat():
    user_id = session['user_id']
    user_type = session['user_type']
    regular_chats = []
    complaint_chats = []

    if user_type == 'A':
        chats = conn.execute(text("""
            select user_id from user where user_type = 'B'
        """)).fetchall()
        for chat in chats:
            print(f'{chat[0]}""""""""""""""""""""""""""""""""""""""""""""""""""""""""')
            temp = conn.execute(text("""
            SELECT chat_id FROM chat
            WHERE (
                (user_id = :user_id AND admin_id = :admin_id) OR
                (user_id = :admin_id AND admin_id = :user_id)
            )
                AND chat_type NOT IN ('return', 'refund', 'warranty')
            """), {
                'user_id': user_id,
                'admin_id': chat
            }).fetchone()

            if temp == None:
                conn.execute(text("""
                    insert into chat (user_id, admin_id)
                    values (:user_id, :other_user_id)
                """), {
                    'user_id': user_id,
                    'other_user_id': chat[0]
                })
                conn.commit()
        complaints = conn.execute(text("""
            select co.complaint_id, co.complaint_type, p.user_id as admin_id
            from complaints co
            join product p on co.product_id = p.product_id
            where co.user_id = :user_id
            and co.status != 'complete'
        """), {
            'user_id': user_id
        }).fetchall()

        for complaint in complaints:
            chat_exists = conn.execute(text("""
                select chat_id from chat
                where user_id = :uid and admin_id = :aid and chat_type = :ctype
            """), {
                'uid': user_id,
                'aid': complaint.admin_id,
                'ctype': complaint.complaint_type
            }).fetchone()

            if chat_exists is None:
                conn.execute(text("""
                    insert into chat (user_id, admin_id, chat_type)
                    values (:uid, :aid, :ctype)
                """), {
                    'uid': user_id,
                    'aid': complaint.admin_id,
                    'ctype': complaint.complaint_type
                })
                conn.commit()
        regular_chats = conn.execute(text("""
            select ch.chat_id, ch.chat_type, b.name as admin_name, b.email
            from chat ch
            join user b on ch.admin_id = b.user_id
            where ch.user_id = :user_id
            and ch.chat_type = 'regular'
        """), {'user_id': user_id}).fetchall()
        complaint_chats = conn.execute(text("""
            select ch.chat_id, ch.chat_type, b.name as admin_name, b.email
            from chat ch
            join user b on ch.admin_id = b.user_id
            where ch.user_id = :user_id
            and ch.chat_type in ('return', 'refund', 'warranty')
        """), {'user_id': user_id}).fetchall()

    elif user_type == 'B':
        chats = conn.execute(text("""
            select user_id from user where user_type = 'A'
        """)).fetchall()
        for chat in chats:
            temp = conn.execute(text("""
            SELECT chat_id FROM chat
            WHERE (
                (user_id = :user_id AND admin_id = :admin_id) OR
                (user_id = :admin_id AND admin_id = :user_id)
            )
                AND chat_type NOT IN ('return', 'refund', 'warranty')
            """), {
            'user_id': user_id,
            'admin_id': chat[0]
            }).fetchone()
            
            if temp == None:
                conn.execute(text("""
                    insert into chat (user_id, admin_id)
                    values (:user_id, :other_user_id)
                """), {
                    'user_id': user_id,
                    'other_user_id': chat[0]
                })
        complaints = conn.execute(text("""
            select complaint_id, user_id, complaint_type
            from complaints
            where (user_id = :admin_id or product_id = :admin_id)
            and status != 'complete'
        """), {'admin_id': user_id}).fetchall()

        for complaint in complaints:
            chat_exists = conn.execute(text("""
                select chat_id from chat
                where user_id = :uid and admin_id = :aid and chat_type = :ctype
            """), {
                'uid': complaint.user_id,
                'aid': user_id,
                'ctype': complaint.complaint_type
            }).fetchone()

            if chat_exists is None:
                conn.execute(text("""
                    insert into chat (user_id, admin_id, chat_type)
                    values (:uid, :aid, :ctype)
                """), {
                    'uid': complaint.user_id,
                    'aid': user_id,
                    'ctype': complaint.complaint_type
                })
                conn.commit()

        regular_chats = conn.execute(text("""
            select ch.chat_id, ch.chat_type, b.name as admin_name, b.email
            from chat ch
            join user b on ch.admin_id = b.user_id
            where ch.user_id = :user_id
            and ch.chat_type = 'regular'
        """), {'user_id': user_id}).fetchall()
        print(f'::::::::::::::{regular_chats}:::::::::::')
        if regular_chats is None:
                ids = conn.execute(text("""
                    select user_id as admin_id
                    from user
                    where user_type = 'A'
                """)).fetchall()
                print(f'::::::::::::::{ids}:::::::::::')
                for id in ids:
                    conn.execute(text("""
                        insert into chat (user_id, admin_id, chat_type)
                        values (:uid, :aid)
                    """), {
                        'uid': user_id,
                        'aid': id.admin_id
                    })
                conn.commit()
        regular_chats = conn.execute(text("""
            select ch.chat_id, ch.chat_type, b.name as admin_name, b.email
            from chat ch
            join user b on ch.admin_id = b.user_id
            where ch.user_id = :user_id
            and ch.chat_type = 'regular'
        """), {'user_id': user_id}).fetchall()

        complaint_chats = conn.execute(text("""
            select ch.chat_id, ch.chat_type, 
            a.name as user_name, a.email,
            co.complaint_id, co.title, co.description, co.status, co.complaint_date
            from chat ch
            join user a on ch.user_id = a.user_id
            join complaints co 
            on ch.user_id = co.user_id 
            and ch.chat_type = co.complaint_type
            where ch.admin_id = :admin_id
            and ch.chat_type in ('return', 'refund', 'warranty')
            and co.status != 'complete'
        """), {'admin_id': user_id}).fetchall()
        return render_template('chat.html', regular_chats=regular_chats, complaint_chats=complaint_chats, bob=1)
    elif user_type == 'C':
        complaints = conn.execute(text("""
            select complaint_id, user_id, complaint_type
            from complaints
            where (user_id = :admin_id or product_id = :admin_id)
            and status != 'complete'
        """), {'admin_id': user_id}).fetchall()
        for complaint in complaints:
            chat_exists = conn.execute(text("""
                select chat_id from chat
                where user_id = :uid and admin_id = :aid and chat_type = :ctype
            """), {
                'uid': complaint.user_id,
                'aid': user_id,
                'ctype': complaint.complaint_type
            }).fetchone()

            if chat_exists is None:
                conn.execute(text("""
                    insert into chat (user_id, admin_id, chat_type)
                    values (:uid, :aid, :ctype)
                """), {
                    'uid': complaint.user_id,
                    'aid': user_id,
                    'ctype': complaint.complaint_type
                })
                conn.commit()
        complaint_chats = conn.execute(text("""
            select ch.chat_id, ch.chat_type, 
            a.name as user_name, a.email,
            co.complaint_id, co.title, co.description, co.status, co.complaint_date
            from chat ch
            join user a on ch.user_id = a.user_id
            join complaints co 
            on ch.user_id = co.user_id 
            and ch.chat_type = co.complaint_type
            where ch.admin_id = :admin_id
            and ch.chat_type in ('return', 'refund', 'warranty')
            and co.status != 'complete'
        """), {'admin_id': user_id}).fetchall()
    return render_template('chat.html', complaint_chats=complaint_chats, bob=1)

@user_bp.route('/view_chat', methods=['POST', 'GET'])
def view_chat():
    user_id = session['user_id']
    chat_id = request.form.get('chat_id') or request.args.get('chat_id')
    chat_type = request.form.get('chat_type') or request.args.get('chat_type')
    other_user_id = conn.execute(text("""
        select admin_id from chat where chat_id = :chat_id
    """), {
        'user_id': user_id,
        'chat_id': chat_id
    }).fetchone()
    if not other_user_id:
        return "Chat not found or access denied"
    name = conn.execute(text("""
        select name from user where user_id = :user_id
    """), {'user_id': user_id}).fetchone()
    other_name = conn.execute(text("""
        select name from user where user_id = :other_user_id
    """), {'other_user_id': other_user_id[0]}).fetchone()
    messages = conn.execute(text("""
        select user_id, text, image, msg_date
        from msg
        where chat_id = :chat_id
        and msg_type = :chat_type
        order by msg_date asc
    """), {
        'chat_id': chat_id,
        'chat_type': chat_type
    }).fetchall()

    return render_template('chat.html', messages=messages, chat=chat_id, name=name, other_name=other_name)

@user_bp.route('/msg', methods=['GET', 'POST'])
def msg():
    chat_id = request.form.get('chat_id')
    user_id = session['user_id']
    msg = request.form.get('text')
    image = request.files.get('image')
    UPLOAD_FOLDER = os.path.join('static', 'uploads')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    if image and image.filename:
        filename = secure_filename(image.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        image.save(file_path)
        image_path = os.path.join('static', 'uploads', filename)
    else:
        image_path = None
    chat_type = conn.execute(text("""
        select chat_type from chat
        where chat_id = :chat_id
    """), {
        'chat_id': chat_id
    }).fetchone()
    chat_type = chat_type[0]
    conn.execute(text("""
        insert into msg (chat_id, user_id, text, image, msg_type)
        values (:chat_id, :user_id, :text, :image, :msg_type)
    """), {
        'chat_id': chat_id,
        'user_id': user_id,
        'text': msg,
        'image': image_path,
        'msg_type': chat_type
    })
    conn.commit()
    return redirect(url_for('user.view_chat', chat_id=chat_id, chat_type=chat_type))


@user_bp.route('/products', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        flash("Please log in to add items to cart")
        return redirect(url_for('user.login'))

    user_id = session['user_id']
    product_id = request.form['product_id']
    color_hex = request.form['color']
    size_label = request.form['size']
    quantity = int(request.form['quantity'])

    with engine.begin() as conn:
        cart = conn.execute(text("""
            SELECT cart_id FROM cart WHERE user_id = :user_id
        """), {'user_id': user_id}).fetchone()

        if not cart:
            conn.execute(text("""
                INSERT INTO cart (user_id) VALUES (:user_id)
            """), {'user_id': user_id})
            cart = conn.execute(text("""
                SELECT cart_id FROM cart WHERE user_id = :user_id
            """), {'user_id': user_id}).fetchone()

        cart_id = cart.cart_id

 
        color = conn.execute(text("""
            SELECT color_id FROM colors WHERE color = :color
        """), {'color': color_hex}).fetchone()

        size = conn.execute(text("""
            SELECT size_id FROM sizes WHERE size = :size
        """), {'size': size_label}).fetchone()

        if not color or not size:
            flash("Invalid color or size selected.")
            return redirect(url_for('user.cart'))

    
        variant = conn.execute(text("""
            SELECT variant_stock FROM product_variants
            WHERE product_id = :product_id 
            AND color_id = :color_id 
            AND size_id = :size_id
        """), {
            'product_id': product_id,
            'color_id': color.color_id,
            'size_id': size.size_id
        }).fetchone()

        if not variant or variant.variant_stock < quantity:
            flash("Selected variant is out of stock or does not exist.")
            return redirect(url_for('user.cart'))

        # Add to cart
        try:
            conn.execute(text("""
                INSERT INTO cart_items (cart_id, product_id, color_id, size_id, quantity)
                VALUES (:cart_id, :product_id, :color_id, :size_id, :quantity)
                ON DUPLICATE KEY UPDATE quantity = quantity + :quantity
            """), {
                'cart_id': cart_id,
                'product_id': product_id,
                'color_id': color.color_id,
                'size_id': size.size_id,
                'quantity': quantity
            })
            flash("Item added to cart!")
        except Exception as e:
            flash(f"Error adding to cart: {str(e)}")
            return redirect(url_for('products.product_gallery'))

    return redirect(url_for('user.cart'))

@user_bp.route('/products', methods=['GET'])
def view_products():
    query = request.args.get('query', '').lower()
    size_filter = request.args.get('size')
    in_stock = request.args.get('in_stock')

    today = date.today()

    products_query = """
    SELECT p.product_id,
           p.title,
           p.description,
           p.price,
           p.warranty,
           MAX(d.discount_amount) AS discount_amount,
           GROUP_CONCAT(DISTINCT c.color) AS colors,
           GROUP_CONCAT(DISTINCT s.size) AS sizes,
           GROUP_CONCAT(DISTINCT i.image) AS images,
           SUM(v.variant_stock) AS stock
    FROM product p
    LEFT JOIN product_variants v ON p.product_id = v.product_id
    LEFT JOIN colors c ON v.color_id = c.color_id
    LEFT JOIN sizes s ON v.size_id = s.size_id
    LEFT JOIN product_images pi ON p.product_id = pi.product_id
    LEFT JOIN images i ON pi.image_id = i.image_id
    LEFT JOIN discounts d ON p.product_id = d.product_id
    WHERE (:query = '' OR LOWER(p.title) LIKE :like_query OR LOWER(p.description) LIKE :like_query)
    GROUP BY p.product_id
"""

    params = {
        'query': query,
        'like_query': f"%{query}%",
        'today': today
    }

    rows = conn.execute(text(products_query), params).fetchall()

    products = []
    all_sizes = set()

    for row in rows:
        product_sizes = row.sizes.split(',') if row.sizes else []
        product_colors = row.colors.split(',') if row.colors else []
        product_images = row.images.split(',') if row.images else []

        if size_filter and size_filter not in product_sizes:
            continue
        if in_stock == "1" and row.stock <= 0:
            continue

        discount_price = None
        if row.discount_amount and row.discount_amount > 0:
            discount_price = round(row.price * (1 - row.discount_amount / 100), 2)

        all_sizes.update(product_sizes)

        products.append({
            'product_id': row.product_id,
            'title': row.title,
            'description': row.description,
            'price': row.price,
            'discount_amount': row.discount_amount,
            'discount_price': discount_price,
            'warranty': row.warranty,
            'stock': row.stock,
            'sizes': product_sizes,
            'colors': product_colors,
            'images': product_images,
        })

    return render_template('all_products.html', products=products, all_sizes=sorted(all_sizes))


@user_bp.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('user.login'))
        
    with engine.connect() as conn:
        cart_items = conn.execute(text("""
            SELECT 
                ci.cart_id,
                ci.product_id,
                ci.color_id,
                ci.size_id,
                ci.quantity,
                p.title, 
                p.price, 
                c.color, 
                s.size, 
                (p.price * ci.quantity) as subtotal,
                (
                    SELECT i.image 
                    FROM product_images pi
                    JOIN images i ON pi.image_id = i.image_id
                    WHERE pi.product_id = p.product_id
                    LIMIT 1
                ) as image_path
            FROM cart_items ci
            JOIN product p ON ci.product_id = p.product_id
            JOIN colors c ON ci.color_id = c.color_id
            JOIN sizes s ON ci.size_id = s.size_id
            WHERE ci.cart_id = (
                SELECT cart_id FROM cart WHERE user_id = :user_id
            )
        """), {'user_id': session['user_id']}).fetchall()
        
        total = sum(item.subtotal for item in cart_items) if cart_items else 0
        
    return render_template('cart.html', cart_items=cart_items, total=total)



@user_bp.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    if 'user_id' not in session:
        return redirect(url_for('user.login'))
        
    product_id = request.form['product_id']
    color_id = request.form['color_id']
    size_id = request.form['size_id']
    
    with engine.begin() as conn:
        cart_id = conn.execute(text("""
            SELECT cart_id FROM cart WHERE user_id = :user_id
        """), {'user_id': session['user_id']}).fetchone().cart_id
        
        conn.execute(text("""
            DELETE FROM cart_items
            WHERE cart_id = :cart_id
            AND product_id = :product_id
            AND color_id = :color_id
            AND size_id = :size_id
        """), {
            'cart_id': cart_id,
            'product_id': product_id,
            'color_id': color_id,
            'size_id': size_id
        })
    
    flash("Item removed from cart")
    return redirect(url_for('user.cart'))

@user_bp.route('/order', methods=['GET', 'POST'])
def place_order():
    user_id = session['user_id']
    address = conn.execute(text("""
        select default_address from user_address where 
        default_address = 1
        and user_id = :user_id
    """), {
        'user_id': user_id
    }).fetchone()
    print(f'{address})))))))))))))))))))))))(((((())))))')
    if not address:
        return redirect(url_for('user.address', e='Please set default address'))
    conn.execute(text("""
        insert into orders (user_id)
        values
        (:user_id)
    """), {
        'user_id': user_id
    })
    conn.commit()

    order_id = conn.execute(text("""
        select order_id from orders where user_id = :user_id 
    """), {
        'user_id': user_id
    }).fetchone()[0]

    items = conn.execute(text("""
        select product_id from cart_items where cart_id = :user_id
    """), {
        'user_id': user_id
    }).fetchall()

    for item in items:

        conn.execute(text("""
        insert into order_products (order_id, product_id)
        values
        (:order_id, :product_id)
        """), {
            'order_id': order_id,
            'product_id': item[0]
        })
    
    conn.execute(text("""
    delete from cart_items where cart_id = :user_id
    """), {
      'user_id': user_id
    })
    conn.commit()
    return redirect(url_for('user.cart'))

@user_bp.route('/view_orders', methods=['GET', 'POST'])
def view_orders():
    user_type = session['user_type']
    user_id = session['user_id']
    if user_type == 'A':
        order_ids = conn.execute(text("""
            select order_id from orders where user_id = :user_id and status = "confirmed"
        """), {
            'user_id': user_id
        }).fetchall()
        order_ids_pen = conn.execute(text("""
            select order_id from orders where user_id = :user_id and status = "pending"
        """), {
            'user_id': user_id
        }).fetchall()
        print(f':::::::::::::::::::::::::::::::::::::::::::::::::{order_ids_pen};;;;;;;;;;;;;;;;;;;;;')
        order_items = []
        order_items_pen = []
        for order_row in order_ids:
            order_id = order_row[0]
            items = conn.execute(text("""
                select product_id from order_products where order_id = :order_id
            """), {
                'order_id': order_id
            }).fetchall()
            for item in items:
                product = conn.execute(text("""
                    select p.product_id, p.title, p.price, i.image
                    from product p
                    left join product_images pi on p.product_id = pi.product_id
                    left join images i on pi.image_id = i.image_id
                    where p.product_id = :product_id
                """), {
                    'product_id': item[0]
                }).fetchone()

                temp = conn.execute(text("""
                    select *
                    from reviews
                    where product_id = :product_id AND user_id = :user_id
                """), {
                    'product_id': product.product_id,
                    'user_id': user_id
                }).fetchall()
                print(f'{temp}))))))))))))))))))))))))))))))))))))')
                if not temp:
                    temp = 0
                else:
                    temp = 1
                order_items.append({
                    'product_id': product.product_id,
                    'title': product.title,
                    'image': product.image,
                    'temp': temp
                })
        for order_row_pen in order_ids_pen:
            order_id = order_row_pen[0]
            items = conn.execute(text("""
                select product_id from order_products where order_id = :order_id
            """), {
                'order_id': order_id
            }).fetchall()
            for item in items:
                product = conn.execute(text("""
                    select p.product_id, p.title, p.price, i.image
                    from product p
                    left join product_images pi on p.product_id = pi.product_id
                    left join images i on pi.image_id = i.image_id
                    where p.product_id = :product_id
                """), {
                    'product_id': item[0]
                }).fetchone()
                order_items_pen.append({
                    'product_id': product.product_id,
                    'title': product.title,
                    'image': product.image,
                })
        return render_template('orders.html', order_items=order_items, order_items_pen=order_items_pen, user_type=user_type)

    if user_type == 'B':
        user_orders = conn.execute(text("""
            select o.order_id, o.user_id, u.name, u.email 
            from orders o
            join user u on o.user_id = u.user_id
        """)).fetchall()
        grouped_orders = {}

        for user_order in user_orders:
            user_id = user_order.user_id

            status = conn.execute(text("""
                select status from orders where order_id = :order_id
            """), {
                'order_id': user_order.order_id
            }).fetchone()
            if user_id not in grouped_orders:
                grouped_orders[user_id] = {
                    'name': user_order.name,
                    'email': user_order.email,
                    'status': status[0],
                    'orders': {}
                }
            products = conn.execute(text("""
                select p.title, i.image
                from order_products op
                join product p on op.product_id = p.product_id
                left join product_images pi on p.product_id = pi.product_id
                left join images i on pi.image_id = i.image_id
                where op.order_id = :order_id
            """), {
                'order_id': user_order.order_id
            }).fetchall()

            product_list = []
            for product in products:
                product_list.append({
                    'title': product.title,
                    'image': product.image
                })
            grouped_orders[user_id]['orders'][user_order.order_id] = product_list
        return render_template('orders.html', user_type=user_type, grouped_orders=grouped_orders, status=status)

@user_bp.route('/approve_order', methods=['POST'])
def approve_order():
    order_id = request.form['order_id']
    order = conn.execute(text("""
        select status from orders where order_id = :order_id
    """), {'order_id': order_id}).fetchone()

    if order and order.status == 'pending':
        conn.execute(text("""
            update orders set status = 'confirmed' where order_id = :order_id
        """), {'order_id': order_id})
        conn.commit()
        return redirect(url_for('user.view_orders'))
    return redirect(url_for('user.view_orders'))

@user_bp.route('/reject_order', methods=['POST'])
def reject_order():
    order_id = request.form['order_id']
    order = conn.execute(text("""
        select status from orders where order_id = :order_id
    """), {'order_id': order_id}).fetchone()

    if order and order.status == 'pending':
        conn.execute(text("""
            update orders set status = 'rejected' where order_id = :order_id
        """), {'order_id': order_id})
        conn.commit()
        return redirect(url_for('user.view_orders'))
    return redirect(url_for('user.view_orders'))

@user_bp.route('/review', methods=['GET', 'POST'])
def review():
    user_type = session['user_type']
    user_id = session['user_id']
    print(f'{user_type}ffffffffffffffffffffffffffffffffffff')
    if user_type == 'A':
        product_id = request.form['product_id']
        reviews = conn.execute(text("""
            select * from reviews where product_id = :product_id and user_id = :user_id
        """), {
            'product_id': product_id,
            'user_id': user_id
        }).fetchall()
        if reviews:
            return render_template('reviews.html', product=reviews, user_type=user_type)
        products = conn.execute(text("""
            select p.title, p.price, i.image, p.description, p.product_id
            from product p
            left join product_images pi on p.product_id = pi.product_id
            left join images i on pi.image_id = i.image_id
            where p.product_id = :product_id
        """), {
            'product_id': product_id
        }).fetchall()
    if user_type == 'B':
        reviews = conn.execute(text("""
            select r.*
            from reviews r
            join product p on r.product_id = p.product_id
            where p.user_id = :user_id
        """), {
            'user_id': user_id
        }).fetchall()
        print(f'{reviews}ffffffffffffffffffffffffffffffffffff')
        if reviews:
            return render_template('reviews.html', product=reviews, user_type=user_type)
        products = conn.execute(text("""
            select p.title, p.price, i.image, p.description, p.product_id
            from product p
            left join product_images pi on p.product_id = pi.product_id
            left join images i on pi.image_id = i.image_id
            where p.product_id = :product_id
        """), {
            'product_id': product_id
        }).fetchall()
    return render_template('reviews.html', products=products, user_type=user_type)

@user_bp.route('/view_reviews', methods=['GET', 'POST'])
def view_reviews():
    user_type = session['user_type']
    user_id = session['user_id']
    sort_by = request.args.get('sort_by')

    order_clause = ""
    if sort_by == 'date_desc':
        order_clause = "ORDER BY review_date DESC"
    elif sort_by == 'date_asc':
        order_clause = "ORDER BY review_date ASC"
    elif sort_by == 'rating_desc':
        order_clause = "ORDER BY rating DESC"
    elif sort_by == 'rating_asc':
        order_clause = "ORDER BY rating ASC"

    if user_type == 'A':
        try:
            query = f"SELECT * FROM reviews WHERE user_id = :user_id {order_clause}"
            reviews = conn.execute(text(query), {'user_id': user_id}).fetchall()
        except:
            return render_template('reviews.html')

        product_id = conn.execute(text("""
            SELECT product_id FROM reviews WHERE user_id = :user_id LIMIT 1
        """), {'user_id': user_id}).fetchone()

        info = []
        if product_id:
            info = conn.execute(text("""
                SELECT p.*, i.image FROM product p
                JOIN product_images pi ON p.product_id = pi.product_id
                JOIN images i ON pi.image_id = i.image_id
                WHERE p.product_id = :product_id
            """), {'product_id': product_id[0]}).fetchall()

        return render_template('reviews.html', reviews=reviews, user_type=user_type, info=info)

    if user_type == 'B':
        try:
            query = f"SELECT * FROM reviews WHERE user_id = :user_id {order_clause}"
            reviews = conn.execute(text(query), {'user_id': user_id}).fetchall()
        except:
            return render_template('reviews.html')
        products = conn.execute(text("""
            SELECT 
                p.title, 
                p.description, 
                p.price, 
                p.stock,
                r.rating, 
                r.description AS review_description, 
                r.image AS review_image, 
                r.review_date,
                i.image AS product_image
            FROM product p
            INNER JOIN reviews r ON p.product_id = r.product_id
            LEFT JOIN product_images pi ON p.product_id = pi.product_id
            LEFT JOIN images i ON pi.image_id = i.image_id
            WHERE p.user_id = :user_id
        """), {'user_id': user_id}).fetchall()
        print(f'{products}ffffffffffffffffffffffffffffffffffff')
        return render_template('reviews.html', products=products, user_type=user_type)

@user_bp.route('/delete_review', methods=['GET', 'POST'])
def delete_review():
    review_id = request.form.get('review_id')

    conn.execute(text("""
        delete from reviews where review_id = :review_id
    """), {
        'review_id': review_id
    })
    conn.commit()
    return redirect(url_for('user.view_reviews'))

@user_bp.route('/post_review', methods=['GET', 'POST'])
def post_review():
    if request.method == 'POST':
        product_id = request.form['product_id']
        user_id = session['user_id']
        rating = request.form['rating']
        description = request.form['description']
        image = request.files['image']
        now = datetime.now()
        review_date = now.strftime("%Y-%m-%d")
        try:
            conn.execute(text("""
                insert into reviews (user_id, product_id, rating, description, image, review_date)
                values
                (:user_id, :product_id, :rating, :description, :image, :review_date)
            """), {
                'user_id': user_id,
                'product_id': product_id,
                'rating': rating,
                'description': description,
                'image': image,
                'review_date': review_date
            })
            conn.commit()
        except Exception as e:
            flash(f"Review submission failed: {e}", "danger")
    return redirect(url_for('user.user'))

@user_bp.route('/complaint', methods=['GET', 'POST'])
def complaint():
    user_type = session['user_type']
    user_id = session['user_id']

    if user_type == 'A':
        product_id = request.form.get('product_id')
        products = conn.execute(text("""
            select p.title, p.price, i.image, p.description, p.product_id
            from product p
            left join product_images pi on p.product_id = pi.product_id
            left join images i on pi.image_id = i.image_id
            where p.product_id = :product_id
        """), {
            'product_id': product_id
        }).fetchall()

        complaints = conn.execute(text("""
            select * from complaints where user_id = :user_id and product_id = :product_id
        """), {
            'user_id': user_id,
            'product_id': product_id
        }).fetchall()
        print(f'{complaints}HHHHHHHHHHJJJJJJJFFFFFFFFFF')
        if complaints:
            return render_template('complaints.html', user_type=user_type, products=products, complaints=complaints)
        else:
            return render_template('complaints.html', user_type=user_type, products=products)  
    if user_type == 'B':
        complaints = conn.execute(text("""
            select c.user_id, c.product_id, c.description, c.title, c.complaint_type, c.status, c.complaint_id, u.username, 
            p.title as product_title,
            i.image as product_image
            from complaints c
            join product p on c.product_id = p.product_id
            join user u on c.user_id = u.user_id
            left join product_images pi on p.product_id = pi.product_id
            left join images i on pi.image_id = i.image_id
            where p.product_id = :user_id;
        """), {
            'user_id': user_id
        }).fetchall()
    return render_template('complaints.html', user_type=user_type, complaints=complaints)

@user_bp.route('/post_complaint', methods=['POST'])
def post_complaint():
    user_id = session['user_id']
    product_id = int(request.form['product_id'])
    title = request.form['title']
    description = request.form['description']
    complaint_type = request.form['complaint']
    complaints = conn.execute(text("""
            select complaint_id from complaints where user_id = :user_id and product_id = :product_id
        """), {
            'user_id': user_id,
            'product_id': product_id
        }).fetchone()
    if not complaints:
        conn.execute(text("""
            insert into complaints (user_id, product_id, complaint_type, complaint_date, title, description, status)
            value (:user_id, :product_id, :complaint_type, now(), :title, :description, 'pending')
        """), {
            'user_id': user_id,
            'product_id': product_id,
            'complaint_type': complaint_type,
            'title': title,
            'description': description
    })
    else:
        conn.execute(text("""
            update complaints set 
            complaint_type = :complaint_type,
            complaint_date = now(),
            title = :title,
            description = :description,
            status = 'pending'
            where complaint_id = :complaint_id
        """), {
        'complaint_type': complaint_type,
        'title': title,
        'description': description,  
        'complaint_id': complaints[0]
        })
    conn.commit()
    return redirect(url_for('user.user'))

@user_bp.route('/update_complaint_status', methods=['POST'])
def update_complaint_status():
    complaint_id = request.form['complaint_id']
    action = request.form['action']
    print(f'fffffffffffffffffffffffffffffffffffff{complaint_id}')
    if action == 'confirm':
        new_status = 'confirmed'
    elif action == 'reject':
        new_status = 'rejected'
    elif action == 'process':
        new_status = 'processing'
    elif action == 'complete':
        new_status = 'complete'
    conn.execute(text("""
        update complaints 
        set status = :new_status 
        where complaint_id = :complaint_id
    """), {
        'new_status': new_status,
        'complaint_id': complaint_id
    })
    conn.commit()
    return redirect(url_for('user.complaint'))