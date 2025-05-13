from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from sqlalchemy import create_engine, text
import bcrypt
from db import engine, conn


home_bp = Blueprint("home", __name__, static_folder="static", template_folder="templates")
show_login_form = False
show_signup_form = False
@home_bp.route('/')
def home():
    ids = conn.execute(text("""
        select p.product_id
        from product p
        left join product_images pi on p.product_id = pi.product_id
        left join images i on pi.image_id = i.image_id
        order by product_id desc 
        limit 12
    """)).fetchall()
    ids = list(set(ids))
    unique_ids = conn.execute(text("""
        select p.product_id
        from product p
        left join product_images pi on p.product_id = pi.product_id
        left join images i on pi.image_id = i.image_id
        order by product_id desc 
        limit 12
    """)).fetchall()
    id_count = []
    for id in range(len(unique_ids)):
        temp = ids.count(unique_ids[id])
        id_count.append({
            'product_id': unique_ids[id],
            'count': temp
            })
    products = conn.execute(text("""
        select p.product_id, p.title, p.price, i.image
        from product p
        left join product_images pi on p.product_id = pi.product_id
        left join images i on pi.image_id = i.image_id
        order by product_id desc 
        limit 12
    """)).fetchall()



    try:
        user_id = session['user_id']
    except:
        session.pop('user_type', None)
        return render_template('home.html', products=products, id_count=id_count)
    return render_template('home.html', show_login_form=True, products=products, id_count=id_count)

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
