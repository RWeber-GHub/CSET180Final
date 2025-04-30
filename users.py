from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from sqlalchemy import create_engine, text
import bcrypt
from db import engine, conn
from datetime import datetime

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

@user_bp.route('/chat')
def chat():
    user_id = session['user_id']
    chats = conn.execute(text("""
        select * from chat where user_id = :user_id
    """), {
        'user_id': user_id
    }).fetchall()
    all_chats = []
    for chat in chats:
        chat_id = chat.chat_id
        messages = conn.execute(text("""
            select * from msg where chat_id = :chat_id order by msg_id asc
        """), {
            'chat_id': chat_id
        }).fetchall()
        all_chats.append({
            'chat_id': chat_id,
            'user_id': chat.user_id,
            'admin_id': chat.admin_id,
            'messages': messages
        })
    return render_template('chat.html', chats=all_chats)

@user_bp.route('/products', methods=['GET', 'POST'])
def products():
    user_id = session['user_id']
    if request.method == 'POST':
        product_id = request.form['product_id']
        quantity = int(request.form['quantity'])
        # color

        cart = conn.execute(text("""
            select cart_id from cart where user_id = :user_id
        """), {
            'user_id': user_id
        }).fetchone()
        cart_id = cart.cart_id
        conn.execute(text("""
            insert into cart_items (cart_id, product_id, color_id, size_id, quantity)
            values 
            (:cart_id, :product_id, :color_id, :size_id, :quantity)
            on duplicate key update quantity = quantity + :quantity
        """), {
            'cart_id': cart_id,
            'product_id': product_id,
            'color_id': 1,
            'size_id': 1,
            'quantity': quantity
        })
        conn.commit()
    return redirect(url_for('products.product_gallery'))

@user_bp.route('/cart')
def cart():
    user_id = session['user_id']
    cart = conn.execute(text("""
        select cart_id from cart where user_id = :user_id
    """), {
        'user_id': user_id
    }).fetchone()
    cart_id = cart.cart_id
    items = conn.execute(text("""
        select p.product_id, p.title, p.price, i.image, ci.quantity
        from cart_items ci
        join product p on ci.product_id = p.product_id
        left join product_images pi on p.product_id = pi.product_id
        left join images i on pi.image_id = i.image_id
        where ci.cart_id = :cart_id
    """), {
        'cart_id': cart_id
    }).fetchall()
    cart_items = []
    total = 0
    for item in items:
        subtotal = item.price * item.quantity
        total += subtotal
        cart_items.append({
            'product_id': item.product_id,
            'title': item.title,
            'price': item.price,
            'image': item.image,
            'quantity': item.quantity,
            'subtotal': subtotal
        })
    return render_template('cart.html', cart_items=cart_items, total=total)

@user_bp.route('/delete', methods=['GET', 'POST'])
def delete_item():
    if request.method == 'POST':
        cart_id = session['user_id']
        product_id = request.form['product_id']
        quantity = int(request.form['quantity'])
        if quantity == 1:
            conn.execute(text("delete from cart_items where product_id = :product_id"), {'product_id': product_id})
            conn.commit()
        else:
            conn.execute(text("""
                update cart_items
                set quantity = quantity - 1
                where cart_id = :cart_id
                and product_id = :product_id
            """), {
                'cart_id': cart_id,
                'product_id': product_id,
            })
            conn.commit()
    return redirect(url_for('user.cart'))

@user_bp.route('/order', methods=['GET', 'POST'])
def place_order():
    user_id = session['user_id']
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
        order_items = []
        order_items_pen = []

        for order_row in order_ids:
            order_id = order_row[0]
            print(f'***{order_id}***')
            items = conn.execute(text("""
                select product_id from order_products where order_id = :order_id
            """), {
                'order_id': order_id
            }).fetchall()
            print(f'***{items}***')
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
                })
                if temp:
                    temp = 1 
                else:
                    temp = 0
                order_items.append({
                    'product_id': product.product_id,
                    'title': product.title,
                    'image': product.image,
                    'reviewed': temp
                })
        print(f'***{order_items}***')
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
            # status = conn.execute(text("""select status from orders where order_id = :order_id
            # """), {
            # 'order_id': user_order.order_id
            # }).fetchone()
            if user_id not in grouped_orders:
                grouped_orders[user_id] = {
                    'name': user_order.name,
                    'email': user_order.email,
                    'orders': {}
                }
            products = conn.execute(text("""
                select p.title, i.image
                from order_products op
                join product p on op.product_id = p.product_id
                left join product_images pi on p.product_id = pi.product_id
                left join images i on pi.image_id = i.image_id
                where op.order_id = :order_id
            """), {'order_id': user_order.order_id}).fetchall()

            product_list = []
            for product in products:
                product_list.append({
                    'title': product.title,
                    'image': product.image
                })
            grouped_orders[user_id]['orders'][user_order.order_id] = product_list
        return render_template('orders.html', user_type=user_type, grouped_orders=grouped_orders)

    return render_template('orders.html')

@user_bp.route('/approve_order', methods=['GET', 'POST'])
def approve_order():
    order_id = request.form['order_id']

    conn.execute(text("""
        update orders set status = "confirmed" where order_id = :order_id
    """), {
        'order_id': order_id
    })
    conn.commit()
    return render_template('orders.html')

@user_bp.route('/review', methods=['GET', 'POST'])
def review():
    user_type = session['user_type']
    user_id = session['user_id']
    if user_type == 'A':
        product_id = request.form['product_id']
        product = conn.execute(text("""
            select *
            from reviews
            where product_id = :product_id AND user_id = :user_id
        """), {
            'product_id': product_id,
            'user_id': user_id
        }).fetchall()
        if product:
            return render_template('reviews.html', products=products, user_type=user_type)
        products = conn.execute(text("""
            select p.title, p.price, i.image, p.description, p.product_id
            from product p
            left join product_images pi on p.product_id = pi.product_id
            left join images i on pi.image_id = i.image_id
            where p.product_id = :product_id
        """), {
            'product_id': product_id
        }).fetchall()
        return redirect(url_for('user.user'))
    if user_type == 'B':
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
            INNER JOIN reviews r ON p.product_id = r.product_id  -- Changed to INNER JOIN
            LEFT JOIN product_images pi ON p.product_id = pi.product_id
            LEFT JOIN images i ON pi.image_id = i.image_id
            WHERE p.user_id = :user_id
        """), {
            'user_id': user_id
        }).fetchall()
        print(f'***{products}***')
    return render_template('reviews.html', products=products, user_type=user_type)

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
        product_id = request.form['product_id']
        products = conn.execute(text("""
            select p.title, p.price, i.image, p.description, p.product_id
            from product p
            left join product_images pi on p.product_id = pi.product_id
            left join images i on pi.image_id = i.image_id
            where p.product_id = :product_id
        """), {
            'product_id': product_id
        }).fetchall()

    return render_template('complaints.html', user_type=user_type, products=products)