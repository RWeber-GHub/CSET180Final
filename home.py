from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from sqlalchemy import create_engine, text

home_bp = Blueprint("home", __name__, static_folder="static", template_folder="templates")

conn_str = 'mysql://root:cset155@localhost/ecomdb'
engine = create_engine(conn_str, echo=True)
conn = engine.connect()

@home_bp.route('/')
def home():
    temp = session['type'] = 1
    return render_template('home.html', temp=temp)


# @home_bp.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         result = conn.execute(text("select * from users where username = :username"), 
#             {'username': username, 'password': password}).fetchone()
#         hashed_password = result[5]
#         if bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')):
#             user_id = result[0]
#             session['user_id'] = user_id
#             return redirect(url_for("index"))
#     return render_template('home.html')

# @home_bp.route('/signout', methods=['POST'])
# def process():
#     if request.method == 'POST':
#         session['user_id'] = None
#         return render_template('index.html')

# @home_bp.route('/signup', methods=['GET', 'POST'])
# def signup():
#     if request.method == 'POST':
#         username = request.form['username']
#         first_name = request.form['first_name']
#         last_name = request.form['last_name']
#         password = request.form['password']
#         salt = bcrypt.gensalt()
#         hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
#         try:
#             conn.execute(text("""
#                 INSERT INTO accounts 
#                 (first_name, last_name, username, password, ssn, balance, address, type) 
#                 VALUES (:first_name, :last_name, :phone_num, :username, :password, :ssn, 0, :address, 'A')
#             """), {
#                 'first_name': first_name, 'last_name': last_name, 
#                 'phone_num': phone_num, 'username': username, 
#                 'password': hashed_password.decode('utf-8'),
#                 'ssn': ssn, 'address': address
#             })
#             conn.commit()

#             result = conn.execute(text("SELECT * FROM accounts WHERE username = :username"), 
#                 {'username': username}).fetchone()
            
#             if result:
#                 user_id = result[0]
#                 session['user_id'] = user_id 
#                 return redirect(url_for("index"))

#         except Exception as e:
#             return render_template('signup.html', error=str(e))
    
#     return render_template('signup.html')

