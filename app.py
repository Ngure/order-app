from flask import Flask, request, jsonify, url_for, redirect, render_template
from authlib.integrations.flask_client import OAuth
from datetime import datetime
from functools import wraps
import africastalking
from models import db, Customer, Order
from database import init_db

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Initialize database
with app.app_context():
    init_db()

# Initialize Africa's Talking
africastalking.initialize('sandbox', 'atsk_9db1e110659f96dd7cdc7a62de6daa6c8d96fe80044e94005bc796c9a45fcf6bd3b3da90')
sms = africastalking.SMS

# Initialize OAuth
oauth = OAuth(app)
oauth.register(
    name='google',
    client_id='980956712488-1v1808iqk259rorfmolo5m4co86u57hl.apps.googleusercontent.com',
    client_secret='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',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid profile email',
    },
)

@app.route('/login')
def login():
    redirect_uri = url_for('auth', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route('/auth')
def auth():
    token = oauth.google.authorize_access_token()
    user = oauth.google.parse_id_token(token)
    return jsonify(user)

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            token = oauth.google.authorize_access_token()
            if token:
                return f(*args, **kwargs)
        except:
            return jsonify({"message": "Unauthorized"}), 403
    return decorated

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/customers', methods=['POST'])
def add_customer():
    data = request.form
    new_customer = Customer(
        name=data['name'],
        code=data['code'],
        phone_number=data['phone_number']
    )
    db.session.add(new_customer)
    db.session.commit()
    return redirect(url_for('home', message='Customer added!'))

@app.route('/upload_customers', methods=['POST'])
def upload_customers():
    file = request.files['file']
    if not file:
        return redirect(url_for('home', message='No file uploaded'))

    stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
    csv_input = csv.reader(stream)
    for row in csv_input:
        new_customer = Customer(
            name=row[0],
            code=row[1],
            phone_number=row[2]
        )
        db.session.add(new_customer)
    db.session.commit()
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
    if not file:
        return redirect(url_for('home', message='No file uploaded'))

    stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
    csv_input = csv.reader(stream)
    for row in csv_input:
        new_order = Order(
            item=row[0],
            amount=float(row[1]),
            time=datetime.utcnow(),
            customer_id=int(row[2])
        )
        db.session.add(new_order)
    db.session.commit()
    return redirect(url_for('home', message='Orders uploaded!'))

@app.route('/protected')
@requires_auth
def protected():
    return jsonify({"message": "This is a protected route"})

@app.route('/view_customers')
def view_customers():
    customers = Customer.query.all()
    return render_template('customers.html', customers=customers)

if __name__ == '__main__':
    app.run(debug=True)