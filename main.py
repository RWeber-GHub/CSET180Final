from flask import Flask, render_template, request, redirect, url_for, session, flash, Blueprint
from sqlalchemy import create_engine, text
from home import home_bp
from users import user_bp
import logging
import random
import string
import bcrypt

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.register_blueprint(home_bp, url_prefix='/home')  
app.register_blueprint(user_bp, url_prefix='/userview')

conn_str = 'mysql://root:cset155@localhost/ecomdb'
engine = create_engine(conn_str, echo=True)
conn = engine.connect()

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/base')
def base():
    return render_template('base.html')

if __name__ == '__main__':
    app.run(debug=True)