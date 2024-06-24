import os
from flask import Flask, request, redirect, url_for, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_dance.contrib.google import make_google_blueprint, google
import africastalking
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key_here')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET')

# Initialize db
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'google.login'

# Initialize africastalking
africastalking.initialize(os.getenv('AFRICASTALKING_USERNAME'), os.getenv('AFRICASTALKING_API_KEY'))
sms = africastalking.SMS

# Initialize OAuth2
google_bp = make_google_blueprint(client_id=app.config['GOOGLE_CLIENT_ID'],
                                  client_secret=app.config['GOOGLE_CLIENT_SECRET'],
                                  redirect_to='google_login')
app.register_blueprint(google_bp, url_prefix='/login')

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    time = db.Column(db.DateTime, default=datetime.utcnow)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    message = request.args.get('message')
    return render_template('index.html', message=message)

@app.route('/customers', methods=['POST'])
def add_customer():
    name = request.form['name']
    code = request.form['code']
    phone_number = request.form['phone_number']
    new_customer = Customer(name=name, code=code, phone_number=phone_number)
    db.session.add(new_customer)
    db.session.commit()
    return redirect(url_for('home', message='Customer added!'))

@app.route('/upload_customers', methods=['POST'])
def upload_customers():
    file = request.files['file']
    # Handle file upload and processing...
    return redirect(url_for('home', message='Customers uploaded!'))

@app.route('/orders', methods=['POST'])
def add_order():
    data = request.form
    new_order = Order(
        item=data['item'],
        amount=float(data['amount']),
        time=datetime.utcnow(),
        customer_id=int(data['customer_id'])
    )
    db.session.add(new_order)
    db.session.commit()

    customer = Customer.query.get(int(data['customer_id']))
    if customer:
        try:
            response = sms.send(f"New order for {data['item']} placed.", [customer.phone_number])
            print("SMS Response:", response)
        except Exception as e:
            print(f"Error sending SMS: {e}")
    
    return redirect(url_for('home', message='Order added and SMS sent!'))

@app.route('/upload_orders', methods=['POST'])
def upload_orders():
    file = request.files['file']
    # Handle file upload and processing...
    return redirect(url_for('home', message='Orders uploaded!'))

@app.route('/customers', methods=['GET'])
def view_customers():
    customers = Customer.query.all()
    return render_template('customers.html', customers=customers)

@app.route('/login')
def login():
    if not google.authorized:
        return redirect(url_for('google.login'))
    resp = google.get("/plus/v1/people/me")
    assert resp.ok, resp.text
    email = resp.json()["emails"][0]["value"]
    user = User.query.filter_by(email=email).first()
    if user is None:
        user = User(email=email)
        db.session.add(user)
        db.session.commit()
    login_user(user)
    return redirect(url_for('home'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)