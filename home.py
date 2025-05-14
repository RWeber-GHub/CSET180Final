from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from sqlalchemy import create_engine, text
import bcrypt
from db import engine, conn


home_bp = Blueprint("home", __name__, static_folder="static", template_folder="templates")
show_login_form = False
show_signup_form = False
@home_bp.route('/')
def home():
    products_raw = conn.execute(text("""
        select p.product_id, p.title, p.price, p.description
        from product p
        order by p.product_id desc
        limit 12
    """)).fetchall()
    product_id_map = {}
    for product in products_raw:
        product_id_map[product.product_id] = {
            'title': product.title,
            'price': product.price,
            'description': product.description,
            'images': []  
        }
    product_ids = []
    for product_id in product_id_map:
        product_ids.append(product_id)

    if product_ids:
        placeholders_list = []
        for index in range(len(product_ids)):
            key = f"{index}"
            placeholders_list.append(f":{key}")
        placeholders_string = ', '.join(placeholders_list)
        query = text(f"""
            select pi.product_id, i.image
            from product_images pi
            join images i on pi.image_id = i.image_id
            where pi.product_id IN ({placeholders_string})
        """)
        params = {}
        for index, pid in enumerate(product_ids):
            key = f"{index}"
            params[key] = pid
        images_raw = conn.execute(query, params).fetchall()
        for img in images_raw:
            product_id = img.product_id
            image_url = img.image
            if product_id in product_id_map:
                product_id_map[product_id]['images'].append(image_url)
    products = []
    for pid, data in product_id_map.items():
        product = {
            'product_id': pid,
            'title': data['title'],
            'price': data['price'],
            'description': data['description'],
            'images': data['images']
        }
        products.append(product)
    return render_template('home.html', show_login_form=False, show_signup_form=False, products=products)


@home_bp.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        result = conn.execute(text("select * from user where username = :username"), 
            {'username': username}).fetchone()
        if result and bcrypt.checkpw(password.encode('utf-8'), result[3].encode('utf-8')):
            session['user_type'] = result[5]
            session['user_id'] = result[0]
            return redirect(url_for("user.user"))
        flash("Invalid credentials, please try again.", "danger")
    return render_template('home.html', show_login_form=True)

@home_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        name = first_name + " " + last_name
        password = request.form['password']
        email = request.form['email']
        user_type = request.form['type']
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
        try:
            conn.execute(text("""
                insert into user (name, username, password, email, user_type) 
                values 
                (:name, :username, :password, :email, :user_type)
            """), {
                'name': name, 
                'username': username, 
                'password': hashed_password.decode('utf-8'),
                'email': email,
                'user_type': user_type
            })
            conn.commit()
            result = conn.execute(text("select * from user where email = :email"), 
                {'email': email}).fetchone()
            if result:
                user_id = result[0]
                user_type = result[5]
                session['user_id'] = user_id 
                session['user_type'] = user_type 
                return redirect(url_for("user.user"))
        except Exception as e:
            flash(str(e), "danger")
    return render_template('home.html', show_signup_form=True)
