import unittest
from app import app, db, Customer, Order

class TestAPI(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_home(self):
        result = self.app.get('/')
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Welcome to the Customer Orders API!", result.data)

    def test_add_customer(self):
        result = self.app.post('/customers', data={
            'name': 'Test Customer',
            'code': 'TC001',
            'phone_number': '1234567890'
        })
        self.assertEqual(result.status_code, 302)  # Redirect to home

    def test_add_order(self):
        with app.app_context():
            customer = Customer(name="Test Customer", code="TC001", phone_number="1234567890")
            db.session.add(customer)
            db.session.commit()
            customer_id = customer.id

        result = self.app.post('/orders', data={
            'item': 'Test Item',
            'amount': 100,
            'time': '2023-01-01T00:00:00Z',
            'customer_id': customer_id
        })
        self.assertEqual(result.status_code, 302)  # Redirect to home

if __name__ == '__main__':
    unittest.main()
