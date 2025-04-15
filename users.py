from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from sqlalchemy import create_engine, text

user_bp = Blueprint("users", __name__, static_folder="static", template_folder="templates")

conn_str = 'mysql://root:cset155@localhost/ecomdb'
engine = create_engine(conn_str, echo=True)
conn = engine.connect()

@user_bp.route('/')
def home():
    temp = session['type'] = 1
    return render_template('userview.html', temp=temp)

@user_bp.route('/login')
def login():
    return render_template('index.html')
    