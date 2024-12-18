from flask import Flask, render_template, request, redirect, flash, url_for
import pymysql
import random
import re

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'secret_key'  # For flash messages

# Database connection
conn = pymysql.connect(
    host="localhost",
    user="root",
    password="password",  # Replace with your MySQL password
    database="bank_system"
)
cursor = conn.cursor()

# Helper function to generate a unique 10-digit account number
def generate_account_number():
    """Generate a unique 10-digit account number."""
    while True:
        account_number = random.randint(10**9, 10**10 - 1)  # Ensuring it's a 10-digit number
        cursor.execute("SELECT account_number FROM accounts WHERE account_number = %s", (account_number,))
        if not cursor.fetchone():
            return account_number

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/create_account', methods=['GET', 'POST'])
def create_account():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        contact_number = request.form['contact_number']
        city = request.form['city']
        state = request.form['state']
        try:
            initial_deposit = float(request.form['initial_deposit'])
        except ValueError:
            flash("Invalid deposit amount.", 'error')
            return redirect(url_for('create_account'))
        pin = request.form['pin']

        # Input validations
        if not re.match(r"^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$", email):
            flash("Invalid email address.", 'error')
            return redirect(url_for('create_account'))

        if not re.match(r"^[0-9]{6}$", pin):
            flash("PIN must be a 6-digit number.", 'error')
            return redirect(url_for('create_account'))

        if contact_number and not re.match(r"^[0-9]{10}$", contact_number):
            flash("Contact number must be a 10-digit number.", 'error')
            return redirect(url_for('create_account'))

        if initial_deposit < 1000:
            flash("Minimum deposit of 1000 is required.", 'error')
            return redirect(url_for('create_account'))

        account_number = generate_account_number()
        query = """
            INSERT INTO accounts (account_number, name, email, contact_number, city, state, balance, pin)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (account_number, name, email, contact_number, city, state, initial_deposit, pin)

        try:
            cursor.execute(query, values)
            conn.commit()
            flash(f"Account created successfully! Your account number is: {account_number}", 'success')
            return redirect(url_for('home'))
        except pymysql.IntegrityError:
            flash("Email already exists. Please use a different email.", 'error')

    return render_template('create_account.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        pin = request.form['pin']

        # Input validations
        if not re.match(r"^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$", email):
            flash("Invalid email address.", 'error')
            return redirect(url_for('login'))

        if not re.match(r"^[0-9]{6}$", pin):
            flash("PIN must be a 6-digit number.", 'error')
            return redirect(url_for('login'))

        query = "SELECT * FROM accounts WHERE email = %s AND pin = %s"
        cursor.execute(query, (email, pin))
        account = cursor.fetchone()

        if account:
            return redirect(url_for('dashboard', account_number=account[0]))
        else:
            flash("Invalid credentials. Please try again.", 'error')

    return render_template('login.html')

@app.route('/dashboard/<int:account_number>')
def dashboard(account_number):
    query = "SELECT * FROM accounts WHERE account_number = %s"
    cursor.execute(query, (account_number,))
    account = cursor.fetchone()
    if not account:
        flash("Account not found.", 'error')
        return redirect(url_for('home'))

    return render_template('dashboard.html', account=account)

@app.route('/credit', methods=['POST'])
def credit():
    account_number = request.form['account_number']
    try:
        amount = float(request.form['amount'])
    except ValueError:
        flash("Invalid amount.", 'error')
        return redirect(url_for('dashboard', account_number=account_number))

    query = "UPDATE accounts SET balance = balance + %s WHERE account_number = %s"
    cursor.execute(query, (amount, account_number))
    conn.commit()

    flash(f"Successfully credited {amount} to your account.", 'success')
    return redirect(url_for('dashboard', account_number=account_number))

@app.route('/debit', methods=['POST'])
def debit():
    account_number = request.form['account_number']
    try:
        amount = float(request.form['amount'])
    except ValueError:
        flash("Invalid amount.", 'error')
        return redirect(url_for('dashboard', account_number=account_number))

    query = "SELECT balance FROM accounts WHERE account_number = %s"
    cursor.execute(query, (account_number,))
    balance = cursor.fetchone()[0]

    if balance >= amount:
        query = "UPDATE accounts SET balance = balance - %s WHERE account_number = %s"
        cursor.execute(query, (amount, account_number))
        conn.commit()
        flash(f"Successfully debited {amount} from your account.", 'success')
    else:
        flash("Insufficient balance.", 'error')

    return redirect(url_for('dashboard', account_number=account_number))

@app.route('/transfer', methods=['POST'])
def transfer():
    from_account = request.form['from_account']
    to_account = request.form['to_account']
    try:
        amount = float(request.form['amount'])
    except ValueError:
        flash("Invalid amount.", 'error')
        return redirect(url_for('dashboard', account_number=from_account))

    query = "SELECT balance FROM accounts WHERE account_number = %s"
    cursor.execute(query, (from_account,))
    balance = cursor.fetchone()[0]

    if balance >= amount:
        cursor.execute("UPDATE accounts SET balance = balance - %s WHERE account_number = %s", (amount, from_account))
        cursor.execute("UPDATE accounts SET balance = balance + %s WHERE account_number = %s", (amount, to_account))
        conn.commit()
        flash(f"Successfully transferred {amount} to account {to_account}.", 'success')
    else:
        flash("Insufficient balance.", 'error')

    return redirect(url_for('dashboard', account_number=from_account))

@app.route('/delete_account/<int:account_number>', methods=['POST'])
def delete_account(account_number):
    query = "DELETE FROM accounts WHERE account_number = %s"
    cursor.execute(query, (account_number,))
    conn.commit()
    flash("Account deleted successfully.", 'success')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
