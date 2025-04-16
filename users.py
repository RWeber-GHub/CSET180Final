from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from sqlalchemy import create_engine, text
import bcrypt
from db import engine, conn


user_bp = Blueprint("user", __name__, static_folder="static", template_folder="templates")

@user_bp.route('/')
def user():
    user_id = session['user_id']
    user = conn.execute(text("select * from user where user_id = :user_id"), 
        {'user_id': user_id}).fetchone()
    return render_template('userview.html', user=user)

@user_bp.route('/chat')
def chat():
    user_id = session['user_id']
    try:
        chats = conn.execute(text("select * from chat where user_id = :user_id"), 
            {'user_id': user_id}).fetchall()
        all_chats = []
        for chat in chats:
            chat_id = chat.chat_id
            messages = conn.execute(text("select * from msg where chat_id = :chat_id order by msg_id asc "), 
                {'chat_id': chat_id}).fetchall()
            all_chats.append({
                'chat_id': chat_id,
                'user_id': chat.user_id,
                'admin_id': chat.admin_id,
                'messages': messages
            })
    except Exception as e:
        return f"Error: {e}"
    return render_template('chat.html', chats=all_chats)

@user_bp.route('/products')
def products():
    info = conn.execute(text("""
        select p.title, p.description, p.stock, p.price, i.image
        from product p
        left join product_images pi on p.product_id = pi.product_id
        left join images i on pi.image_id = i.image_id
        order by p.product_id asc""")).fetchall()
    return render_template('products.html', products=info)