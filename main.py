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
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.register_blueprint(home_bp, url_prefix='/home')  
app.register_blueprint(user_bp, url_prefix='/userview')
app.register_blueprint(products_bp, url_prefix='/products')

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/base')
def base():
    return render_template('base.html')

@app.after_request
def after_request(response):
    if request.path.startswith('/products/') and 'application/json' not in response.content_type:
        if response.status_code >= 400:
            return jsonify({
                'success': False,
                'message': response.status
            }), response.status_code
    return response

if __name__ == '__main__':
    app.run(debug=True)