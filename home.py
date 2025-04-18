from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from sqlalchemy import create_engine, text
import bcrypt
from db import engine, conn


home_bp = Blueprint("home", __name__, static_folder="static", template_folder="templates")

@home_bp.route('/')
def home():
    session.pop('user_type', None)
    session.pop('user_id', None)
    users = conn.execute(text("select * from user")).fetchall()
    return render_template('home.html', users=users)

@home_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        result = conn.execute(text("select * from user where username = :username"), 
            {'username': username}).fetchone()
        hashed_password = result[3]
        if bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')):
            session['user_type'] = result[5]
            session['user_id'] = result[0]
            return redirect(url_for("user.user"))
    return render_template('home.html')

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
            return render_template('home.html', error=str(e))
    return render_template('userview.html')

