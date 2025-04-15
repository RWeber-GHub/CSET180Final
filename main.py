from flask import Flask, render_template, request, redirect, url_for, session, flash, Blueprint
from sqlalchemy import create_engine, text
from db import engine
from db import conn
from home import home_bp
from users import user_bp
from products import products_bp
import logging
import random
import string
import bcrypt

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.register_blueprint(home_bp, url_prefix='/home')  
app.register_blueprint(user_bp, url_prefix='/userview')
app.register_blueprint(products_bp, url_prefix='/products')


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/base')
def base():
    return render_template('base.html')

if __name__ == '__main__':
    app.run(debug=True)