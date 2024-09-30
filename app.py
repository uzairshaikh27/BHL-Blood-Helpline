import os  
from dotenv import load_dotenv
import mysql.connector as mysql
from flask import Flask, jsonify, redirect, request, session, url_for, render_template  
from flask_bcrypt import Bcrypt  
from flask_cors import CORS  
from MySQLdb.constants import CLIENT

from flask_mysqldb import MySQL  
from bcrypt import hashpw, gensalt, checkpw  

load_dotenv()
app = Flask(__name__)

app.secret_key = 'your_secret_key'

bcrypt = Bcrypt(app)
# import mysql.connector as mysql
# conn = mysql.connect(
#     host='127.0.0.1',
#     user='root',       # Make sure this is the correct username
#     passwd='9759856474@Uz',  # Replace 'your_password' with the actual password
#     database='bhl_db'  # The database you want to connect to
# )
# # MySQL configurations
# app.config['MYSQL_USER'] = 'root'
# app.config['MYSQL_PASSWORD'] = '9759856474@Uz'
# app.config['MYSQL_DB'] = 'bhl_db'
# app.config['MYSQL_HOST'] = '127.0.0.1'
# app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

app.config['UPLOAD_FOLDER'] = 'static/uploads/'  # Folder where images will be saved  
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit upload to 16 MB  


# pymysql.install_as_MySQLdb() 
mysql = MySQL(app)


os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)  #CREATE DIECTORY


@app.route('/')
def home():
    return render_template('login.html')
        


@app.route('/index')  
def index_page():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM donation_drive ")
    camps = cursor.fetchall()
    cursor.close()  
     
    return render_template('index.html',camps=camps)
        
  






@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.json
        print(f"Received data: {data}")  # Debugging line to see the incoming data  

        required_fields = ['username', 'email', 'mobile', 'password', 'blood_group', 'age','address', 'city', 'state']  

        for field in required_fields:  
            if field not in data:  
                return jsonify({'error': f'Missing field: {field}'}), 400
            
        email = data['email']   
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))    
        existing_user = cursor.fetchone()

        if existing_user:
            cursor.close()
            return jsonify({'error': 'Email already registered. Please log in.'}), 409  # HTTP 409 Conflict

        username = data['username']
        email = data['email']
        mobile = data['mobile']
        password = data['password']
        blood_group=data['blood_group']
        age=data['age']
        address=data['address']
        city=data['city']
        state=data['state']
        hashed_password = hashpw(password.encode('utf-8'), gensalt())
        cursor = mysql.connection.cursor()
        cursor.execute('''
            INSERT INTO users (username, email, mobile, password,blood_group,age,address,city,state)
            VALUES (%s, %s, %s, %s,%s, %s, %s, %s,%s)
        ''', (username, email, mobile, hashed_password,blood_group,age,address,city,state))

        mysql.connection.commit()
        cursor.close()
        return jsonify({'message': 'User registered successfully'})
    except Exception as e:
        print(f"Error: {e}")  # Print error to console
        return jsonify({'error': 'Database operation failed', 'details': str(e)}), 500
    




@app.route('/login', methods=['POST'])  
def login():  
    try:  
        data = request.json  
        
        # Check if the expected fields are in the request  
        if not data or 'email' not in data or 'password' not in data:  
            return jsonify({'error': 'Missing email or password'}), 400  
            
        email = data['email']  

        password = data['password']  

        cursor = mysql.connection.cursor()  
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))  
        user = cursor.fetchone()  # This should return a tuple or None  

        cursor.close()  
        
        # Check if user was found  
        if user is None:  
            return jsonify({'error': 'Invalid email or password'}), 401  
        
        # Assuming that `user` is a tuple and password is at an index, update as necessary  
        # You may have to adjust index based on your database schema  
        if checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):  
            session['user_id'] = user['id']  
           
            return jsonify({'user_id': user['id']}), 200  
        else:  
            print(f"Password does not match for user with email: {user['email']}")  
            return jsonify({'error': 'Invalid email or password'}), 401  
            
    except Exception as e:  
        print(f"Error: {e}")  # Print error to console for debugging  
        return jsonify({'error': 'Database operation failed', 'details': str(e)}), 500


@app.route('/logout', methods=['POST'])
def logout():
    # Clear the session data
    session.clear()
    # Redirect to the login page
    
    return redirect(url_for('home'))



@app.route('/dashboard', methods=['GET'])
def dashboard():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized access'}), 401

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT donation_date,location,donation_type,blood_group,donation_count FROM donations WHERE user_id = %s", (user_id,))
    donations = cursor.fetchall()

    cursor.execute("SELECT * FROM appointments WHERE user_id = %s", (user_id,))
    appointments = cursor.fetchall()

    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()

    return render_template('dashboard.html', donations=donations, appointments=appointments, user=user)





@app.route('/schedule_appointment', methods=['POST'])
def schedule_appointment():
    data = request.json
    user_id = session.get('user_id')
    appointment_date = data['appointment_date']
    location = data['location']

    cursor = mysql.connection.cursor()
    cursor.execute('''
        INSERT INTO appointments (user_id, appointment_date, location)
        VALUES (%s, %s, %s)
    ''', (user_id, appointment_date, location))

    mysql.connection.commit()
    cursor.close()
    return jsonify({'message': 'Appointment scheduled successfully'})




@app.route('/upload_image', methods=['POST'])  
def upload_image():  
    user_id = session.get('user_id')  
    if not user_id:  
        return jsonify({'error': 'Unauthorized access'}), 401  

    if 'profile_image' not in request.files:  
        return jsonify({'error': 'No file part'}), 400  

    file = request.files['profile_image']  
    if file.filename == '':  
        return jsonify({'error': 'No selected file'}), 400  

    if file:  
        filename = file.filename  
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)  
        file.save(filepath)  

        # Update user profile image path in the database  
        cursor = mysql.connection.cursor()  
        cursor.execute('UPDATE users SET profile_image = %s WHERE id = %s', (filepath, user_id))  
        cursor.execute("UPDATE users SET profile_image = REPLACE(profile_image, 'static/', '') WHERE profile_image LIKE 'static/%'")        
        mysql.connection.commit()  
        cursor.close()  

        return jsonify({'message': 'Image uploaded successfully'})  



@app.route('/add_camp', methods=['POST'])  
def create_drive():  
    # Ensure the user is logged in  
    if 'user_id' not in session:  
        return jsonify({'error': 'Unauthorized access'}), 401  

    user_id = session['user_id']  
    cursor = mysql.connection.cursor()  
    
    # Get the user's email  
    cursor.execute("SELECT email FROM users WHERE id = %s", (user_id,))  
    user = cursor.fetchone()  

    # Check if user exists  
    if user is None:  
        return jsonify({'error': 'User not found'}), 404  

    # Check if the email exists in admin_data table  
    cursor.execute("SELECT * FROM admin_data WHERE email = %s", (user['email'],))  
    admin = cursor.fetchone()  
    
    if admin is None:  
        return jsonify({'error': 'Only admins can create donation drive'}), 403  

    # Proceed with creating the donation drive  
    data = request.json  
    title = data['title']  
    date = data['date']  
    location = data['location']  

    cursor.execute('''  
        INSERT INTO donation_drive (title, date, location)  
        VALUES (%s, %s, %s)  
    ''', (title,  date, location))  

    mysql.connection.commit()  
    cursor.close()  
    return jsonify({'message': 'Donation drive created successfully'})


if __name__ == '__main__':
    app.run(debug=True)


