from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import os
import re
from datetime import timedelta


load_dotenv()
DB_CONNECTION_STRING = os.getenv('DB_CONNECTION_STRING')
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = JWT_SECRET_KEY
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

jwt = JWTManager(app)

conn = psycopg2.connect(DB_CONNECTION_STRING)
cur = conn.cursor()

def validate_email_format(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def validate_password(password):
    if len(password) < 8:
        return False
    return True

@app.route('/signup', methods=['POST'])
def signup():
    try:        
        data = request.form
        
        input_params = ['username', 'email', 'password']
        
        if False in [input in data for input in input_params]:
            return jsonify({'error': 'Missing input'}), 400

        if not validate_email_format(data['email']):
            return jsonify({'error': 'invalid email format'}), 400

        if not validate_password(data['password']):
            return jsonify({'error': 'password should be atleast 8 characters'}), 400
        
        
        cur.execute("SELECT * FROM SuperUsers WHERE email = %s", (data['email'],))
        if cur.fetchone():
            return jsonify({'error': 'email already registered'}), 400

        password_enc = generate_password_hash(data['password'])
        query = " INSERT INTO SuperUsers (Username, Email, Password) VALUES (%s, %s, %s) RETURNING UserID, Username, Email;"
        cur.execute(query, (data['username'], data['email'], password_enc))
        conn.commit()
        new_user = cur.fetchone()
        return jsonify({col:val for col,val in zip(['userid','username','email'],new_user)})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    
@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.form
        if not data or 'email' not in data or 'password' not in data:
            return jsonify({'error': 'Missing input'}), 400
        
        query = "SELECT * FROM SuperUsers WHERE email = %s;"
        cur.execute(query, (data['email'],))
        user = cur.fetchone()
        
        if user and (check_password_hash(user[3], data['password']) or (user[3]==data['password'])) :
            access_token = create_access_token(identity=user[2])
            
            return jsonify({'access_token': access_token}), 200
        
        return jsonify({'error': 'Invalid credentials'}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    
@app.route('/users', methods=['POST'])
def create_user():
    
    try:        
        data = request.form
        
        input_params = ['username', 'email', 'password']
        
        if False in [input in data for input in input_params]:
            return jsonify({'error': 'Missing input'}), 400

        if not validate_email_format(data['email']):
            return jsonify({'error': 'invalid email format'}), 400

        if not validate_password(data['password']):
            return jsonify({'error': 'password should be atleast 8 characters'}), 400
        
        
        cur.execute("SELECT * FROM Users WHERE email = %s", (data['email'],))
        if cur.fetchone():
            return jsonify({'error': 'email already registered'}), 400

        password_enc = generate_password_hash(data['password'])
        query = "\
            INSERT INTO Users (Username, Email, Password) \
            VALUES (%s, %s, %s) \
            RETURNING UserID, Username, Email;\
        "
        cur.execute(query, (data['username'], data['email'], password_enc))
        conn.commit()
        new_user = cur.fetchone()
        return jsonify({col:val for col,val in zip(['userid','username','email'],new_user)})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/users/u/<user_id>',methods=['PUT'])
@jwt_required()
def update_user(user_id):
    try:
        current_user_id = get_jwt_identity()
        
        cur.execute(f"SELECT * FROM SuperUsers WHERE email = '{current_user_id}'")   
        data = cur.fetchone()
        conn.commit()
        if current_user_id not in data:
            return jsonify({'error': 'Unauthorized'}), 400
            
        input_params = ['username', 'email', 'password']
        update_params = []
        values = []
        data = request.form
        print(data)
        for field in input_params:
            if field in data:
                
                if field == 'email' and not validate_email_format(data['email']):
                    return jsonify({'error': 'Invalid email format'}), 400
                
                if field == 'password':
                    if not validate_password(data['password']):
                        return jsonify({'error': 'Invalid password format'}), 400
                    data[field] = generate_password_hash(data[field])
                
                update_params.append(f"{field} = %s")
                values.append(data[field])
        
        if not update_params:
            return jsonify({'error': 'No valid fields to update'}), 400

        values.append(user_id)
        query = f"UPDATE Users SET {', '.join(update_params)} WHERE UserID = %s"
        cur.execute(query, values)
        conn.commit()
        
        return jsonify({'status': 'Updated Successfully'}), 200
    
    except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/users/u/<user_id>',methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    try:
        current_user_id = get_jwt_identity()
        
        cur.execute(f"SELECT * FROM SuperUsers WHERE email = '{current_user_id}'")   
        data = cur.fetchone()
        conn.commit()
        
        if current_user_id not in data:
            return jsonify({'error': 'Unauthorized'}), 400
        orderdet_delete_query = "DELETE FROM OrderDetails WHERE OrderID IN (SELECT OrderID FROM Orders WHERE UserID = %s);"
        cur.execute(orderdet_delete_query,user_id)
        
        order_delete_query = "DELETE from Orders where UserID = %s"
        cur.execute(order_delete_query,user_id)
        
        user_delete_query = "DELETE from Users where UserID = %s"
        cur.execute(user_delete_query,user_id)
        
        conn.commit()
        
        return jsonify({'status': 'Deleted Successfully'}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/products',methods=['POST'])
@jwt_required()
def create_product():
    try:
        current_user_id = get_jwt_identity()
        
        cur.execute(f"SELECT * FROM SuperUsers WHERE email = '{current_user_id}'")   
        data = cur.fetchone()
        conn.commit()
        if current_user_id not in data:
            return jsonify({'error': 'Unauthorized'}), 400
        
        data = request.get_json()
        required_fields = ['productname', 'description', 'price', 'stock']
        if False in [field in data for field in required_fields]:
            return jsonify({'error': 'Missing required fields'}), 400
        
        query = "INSERT INTO Products (ProductName, Description, Price, Stock) \
            VALUES (%s, %s, %s, %s) RETURNING *; """
            
        cur.execute(query, (
            data['productname'],
            data['description'],
            data['price'],
            data['stock']
        ))
        conn.commit()
        new_product = cur.fetchone()
        
        return jsonify(new_product), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/products/<product_id>',methods=['PUT'])
@jwt_required()
def update_product(product_id):
    
    try:
        current_user_id = get_jwt_identity()
        
        cur.execute(f"SELECT * FROM SuperUsers WHERE email = '{current_user_id}'")   
        data = cur.fetchone()
        conn.commit()
        if current_user_id not in data:
            return jsonify({'error': 'Unauthorized'}), 400
            
        product_params = ['productname', 'description', 'price','stock']
        update_params = []
        values = []
        data = request.form
        print(data)
        for field in product_params:
            if field in data:              
                update_params.append(f"{field} = %s")
                values.append(data[field])
        
        if not update_params:
            return jsonify({'error': 'No valid fields to update'}), 400

        values.append(product_id)
        query = f" UPDATE Products SET {', '.join(update_params)} WHERE ProductID = %s ;"""
        cur.execute(query, values)
        conn.commit()
        
        return jsonify({'status': 'Updated Successfully'}), 200
    
    except Exception as e:
            return jsonify({'error': str(e)}), 500
        

@app.route('/orders',methods=['POST'])
@jwt_required()
def create_orders():
    try:        
        current_user_id = get_jwt_identity()
        
        cur.execute(f"SELECT * FROM SuperUsers WHERE email = '{current_user_id}'")   
        data = cur.fetchone()
        conn.commit()
        if current_user_id not in data:
            return jsonify({'error': 'Unauthorized'}), 400
        
        data = request.get_json()
        print(data)
        total_amount = 0
        order_details = []

        user_id = data['user_id']
        
        for product in data['products']:
            cur.execute("SELECT ProductID, Price, Stock \
                FROM Products \
                WHERE ProductID = %s FOR UPDATE ", (str(product['product_id'])))
            
            product_info = cur.fetchone()

            if not product_info:
                raise ValueError(f"Product {product['product_id']} not found")
            
            subtotal = float(product_info[1]) * int(product['quantity'])
            total_amount += subtotal
            
            order_details.append({
                'product_id': product['product_id'],
                'quantity': product['quantity'],
                'subtotal': subtotal
            })
        cur.execute(
            "INSERT INTO Orders (UserID, TotalAmount) VALUES (%s, %s) RETURNING OrderID, OrderDate",
            (user_id, total_amount)
        )
        
        order = cur.fetchone()
        conn.commit()
        order_id = order[0]
        
        for detail in order_details:
            cur.execute("INSERT INTO OrderDetails (OrderID, ProductID, Quantity, SubTotal) VALUES (%s, %s, %s, %s);",
                (order_id, detail['product_id'], detail['quantity'], detail['subtotal'])
            )
        
        conn.commit()

        return jsonify({'status':'success'}),200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/data/<table_name>')
@jwt_required()
def display_table(table_name):

    try:
        current_user_id = get_jwt_identity()
        
        cur.execute(f"SELECT * FROM SuperUsers WHERE email = '{current_user_id}'")   
        data = cur.fetchone()
        conn.commit()
        query = f"SELECT * FROM {table_name};"
        
        if table_name=="accounts":
            query = f"SELECT * FROM orderdetails JOIN orders ON orderdetails.orderid = orders.orderid"
        else:
            query = f"SELECT * FROM {table_name};"
            
        cur.execute(query)
        conn.commit()
        
        column_names = [desc[0] for desc in cur.description]
        records = cur.fetchall()
        
        data = [{j:k for j,k in zip(column_names,record)} for record in records]
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    return jsonify(data)


if __name__ == '__main__':
    app.run(port=8001,debug=True)