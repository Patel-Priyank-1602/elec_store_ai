from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv 
import os
import mysql.connector
import json

load_dotenv()

app = Flask(__name__)
app.secret_key = "ppppp"  
app.config.from_object('config.Config')

# Electronics store database configuration
electronics_db_config = {
    'user': 'root',
    'password': '1234',
    'host': 'localhost',
    'database': 'electronics_store'
}

# PayFlex database configuration
payflex_db_config = {
    'user': 'root',
    'password': '1234',
    'host': 'localhost',
    'database': 'payflex'
}

db = SQLAlchemy(app)

def get_db_connection(config=electronics_db_config):
    return mysql.connector.connect(**config)

def is_logged_in():
    return 'user_id' in session

@app.route('/')
def index():
    if not is_logged_in():
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/payment')
def payment_website():
    if not is_logged_in():
        return redirect(url_for('login'))
    return render_template('payment_website.html')

@app.route('/save_payment_details', methods=['POST'])
def save_payment_details():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    try:
        # Get form data and store in session
        payment_data = {
            'full_name': request.form['full_name'],
            'bank_name': request.form['bank_name'],
            'account_number': request.form['account_number'],
            'mobile_number': request.form['mobile_number'],
            
            'shipping_name': request.form['shipping_name'],
            'shipping_mobile': request.form['shipping_mobile'],
            'shipping_address1': request.form['shipping_address1'],
            'shipping_address2': request.form.get('shipping_address2', ''),
            'shipping_city': request.form['shipping_city'],
            'shipping_state': request.form['shipping_state'],
            'shipping_zip': request.form['shipping_zip'],
            'shipping_country': request.form['shipping_country'],
            'shipping_instructions': request.form.get('shipping_instructions', ''),
            
            'beneficiary_name': request.form.get('beneficiary_name', 'Electronic store'),
            'beneficiary_bank': request.form.get('beneficiary_bank', 'Bank Of Baroda'),
            'beneficiary_account': request.form.get('beneficiary_account', '65345677654321'),
            'beneficiary_mobile': request.form.get('beneficiary_mobile', '9856745680'),
            
            'payment_method': request.form['payment_method']
        }
        
        # Store in session
        session['payment_data'] = payment_data
        
        # Redirect based on payment method
        payment_method = payment_data['payment_method']
        if payment_method == 'Credit/Debit Card':
            return redirect(url_for('card'))
        elif payment_method == 'UPI':
            return redirect(url_for('upi'))
        else:  # Bank Transfer
            return redirect(url_for('nri'))
            
    except Exception as e:
        flash(f'Error processing payment information: {str(e)}', 'error')
        return redirect(url_for('payment_website'))

@app.route('/card')
def card():
    if not is_logged_in() or 'payment_data' not in session:
        return redirect(url_for('payment_website'))
    
    payment_data = session['payment_data']
    return render_template('card.html', payment_data=payment_data)

@app.route('/upi')
def upi():
    if not is_logged_in() or 'payment_data' not in session:
        return redirect(url_for('payment_website'))
    
    payment_data = session['payment_data']
    return render_template('upi.html', payment_data=payment_data)

@app.route('/nri')
def nri():
    if not is_logged_in() or 'payment_data' not in session:
        return redirect(url_for('payment_website'))
    
    payment_data = session['payment_data']
    return render_template('nri.html', payment_data=payment_data)

@app.route('/process_payment', methods=['POST'])
def process_payment():
    if not is_logged_in() or 'payment_data' not in session:
        return redirect(url_for('payment_website'))
    
    try:
        # Get payment data from session
        payment_data = session['payment_data']
        
        # Additional payment specific data from the payment method form
        if 'transaction_reference' in request.form:
            transaction_reference = request.form['transaction_reference']
        else:
            transaction_reference = None
        
        # Connect to PayFlex database
        conn = get_db_connection(payflex_db_config)
        cursor = conn.cursor()
        
        # Insert payment data
        query = '''
        INSERT INTO payments (
            full_name, bank_name, account_number, mobile_number,
            shipping_name, shipping_mobile, shipping_address1, shipping_address2,
            shipping_city, shipping_state, shipping_zip, shipping_country,
            shipping_instructions, payment_method, transaction_status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''
        
        values = (
            payment_data['full_name'], 
            payment_data['bank_name'],
            payment_data['account_number'],
            payment_data['mobile_number'],
            payment_data['shipping_name'],
            payment_data['shipping_mobile'],
            payment_data['shipping_address1'],
            payment_data['shipping_address2'],
            payment_data['shipping_city'],
            payment_data['shipping_state'],
            payment_data['shipping_zip'],
            payment_data['shipping_country'],
            payment_data['shipping_instructions'],
            payment_data['payment_method'],
            'processing'  # Set initial status as processing
        )
        
        cursor.execute(query, values)
        conn.commit()
        payment_id = cursor.lastrowid
        
        cursor.close()
        conn.close()
        
        # Clear payment data from session
        if 'payment_data' in session:
            del session['payment_data']
        
        flash('Payment processed successfully!', 'success')
        return redirect(url_for('payment_status', payment_id=payment_id))
            
    except Exception as e:
        flash(f'Error processing payment: {str(e)}', 'error')
        return redirect(url_for('payment_website'))

@app.route('/payment_status/<int:payment_id>', methods=['GET'])
def payment_status(payment_id):
    if not is_logged_in():
        return redirect(url_for('login'))
    
    conn = get_db_connection(payflex_db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM payments WHERE id = %s', (payment_id,))
    payment = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not payment:
        flash('Payment not found', 'error')
        return redirect(url_for('index'))
        
    return render_template('payment_status.html', payment=payment)

@app.route('/update_payment_status/<int:payment_id>', methods=['POST'])
def update_payment_status(payment_id):
    if not is_logged_in():
        return redirect(url_for('login'))
    
    status = request.form['status']
    
    conn = get_db_connection(payflex_db_config)
    cursor = conn.cursor()
    cursor.execute('UPDATE payments SET transaction_status = %s WHERE id = %s', (status, payment_id))
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Payment status updated successfully', 'success')
    return redirect(url_for('payment_status', payment_id=payment_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_logged_in():
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user and password == user['password']:  
            session['user_id'] = user['id']
            session['email'] = user['email']
            session['name'] = user['name']
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password. Please register if you don\'t have an account.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login', logout='success'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if is_logged_in():
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password'] 
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        if cursor.fetchone():
            flash('Email already registered. Please login.', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('login'))
       
        cursor.execute('INSERT INTO users (name, email, password) VALUES (%s, %s, %s)',
                      (name, email, password))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Registration successful! Please login with your new account.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/api/products', methods=['GET'])
def get_products():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    query = '''
    SELECT p.id, p.name, p.price, p.image_url, p.subcategory_id, s.name AS subcategory, c.name AS category
    FROM products p
    JOIN subcategories s ON p.subcategory_id = s.id
    JOIN categories c ON s.category_id = c.id
    '''
    cursor.execute(query)
    products = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(products)

@app.route('/api/categories', methods=['GET'])
def get_categories():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM categories')
    categories = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(categories)

@app.route('/api/subcategories/<int:category_id>', methods=['GET'])
def get_subcategories(category_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM subcategories WHERE category_id = %s', (category_id,))
    subcategories = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(subcategories)

if __name__ == '__main__':
    app.run(debug=True)