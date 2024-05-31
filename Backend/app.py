from flask import Flask, request, jsonify, Response
import sqlite3
import bcrypt


app = Flask(__name__)
database = 'database.db'

# Function to decorate functions that requiere a connection to the database
def query(database:str): 
    def wrapper(customQuery):
        def wrapFunction(*args,**kwargs):
            # Creates connection to the database and closes it when done
            connection = sqlite3.connect(database)
            cursor = connection.cursor()
            result = customQuery(cursor,connection,*args,**kwargs)
            cursor.close()
            connection.close()
            return result
        return wrapFunction
    return wrapper

# Function to hash a password with bcrypt
def hashPassword(passwordString:str)->str:
    # Converting password to array of bytes 
    bytes = passwordString.encode('utf-8') 
    
    # Generating the salt 
    salt = bcrypt.gensalt() 
    
    # Hashing the password 
    passwordHash = bcrypt.hashpw(bytes, salt) 
    return passwordHash

# Function to validate that the json received includes all the parameters needed
def validateData(parameters:list[str],dictionary:dict)->bool:
    for i in parameters:
        if i not in dictionary:
            return False
    return True

# Function to create the response of the api(mostly used in case of an error)
def responseJson(code:int, motive:str)->Response:
    data = {
        "Status code" : code,
        "Motive" : motive}
    response = jsonify(data)
    response.status_code = code
    return response

@query(database)
def checkAdmin(cursor:sqlite3.Cursor,connection:sqlite3.Connection,id:int)->bool:
    # Retrieve user(will be None in case it's not found)
    data = cursor.execute("SELECT * FROM users WHERE id = ? AND role = 'admin' ", (id,))
    row = data.fetchone()
    if not row:
        return False
    return True

# Creates tables needed for the database



@query(database)
def createTables(cursor:sqlite3.Cursor,connection:sqlite3.Connection):
    cursor.execute("""CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                username VARCHAR(50) NOT NULL, 
                password VARCHAR(50) NOT NULL,
                role VARCHAR(10) NOT NULL,
                firstname VARCHAR(50) NOT NULL,
                middlename VARCHAR(50) NOT NULL,
                lastname VARCHAR(50) NOT NULL,
                points INT NOT NULL DEFAULT 0
               )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS productOrders(
                order_id INTEGER PRIMARY KEY AUTOINCREMENT, 
                customer_id INT NOT NULL,
                order_date DATE NOT NULL DEFAULT CURRENT_DATE,
                FOREIGN KEY (order_id) REFERENCES users(id)
               )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS proposals(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(50) NOT NULL,
                current_situation VARCHAR(50) NOT NULL,
                area VARCHAR(50) NOT NULL,
                status VARCHAR(50) NOT NULL,
                proposal VARCHAR(300) NOT NULL,
                type VARCHAR(50) NOT NULL,
                feedback VARCHAR(50) NOT NULL
               )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS userProposals(
                user_id INT NOT NULL,
                proposal_id INT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (proposal_id) REFERENCES proposals(id)
               )""")   
    cursor.execute("""CREATE TABLE IF NOT EXISTS userProposals(
                user_id INT NOT NULL,
                proposal_id INT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (proposal_id) REFERENCES proposals(id)
               )""")   
    cursor.execute("""CREATE TABLE IF NOT EXISTS products(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(50) NOT NULL,
                description VARCHAR(100) NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                image VARCHAR(100) NOT NULL
               )""")   
    cursor.execute("""CREATE TABLE IF NOT EXISTS orders(
                user_id INT NOT NULL,
                product_id INT NOT NULL,
                quantity INT NOT NULL,
                order_status VARCHAR(50) NOT NULL,
                order_date DATE NOT NULL DEFAULT CURRENT_DATE,
                total DECIMAL(10,2) NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
               )""")   
    connection.commit()  

createTables()


@app.route('/')
def index():
    return 'Hello, World!'

@app.route('/login', methods=["POST"])
def login():
    if request.method == "POST":
        #Login

        # Validate data
        jsonData = request.get_json()
        if validateData(["username","password"],jsonData) == False:
            response = responseJson(400,"Incorrect parameters sent")
            return response
        
        # Get the parameters needed for the login
        username = request.get_json()["username"]
        password = request.get_json()["password"]
        if startSession(username,password):
            data = {
                "Status Code": 200,
                "success":True}
            response = jsonify(data)
            response.status_code = 200
            return response
        else:
            data = {
                "Status Code": 200,
                "success":False}
            response = jsonify(data)
            response.status_code = 200
            return response

# Function to validate the login info
@query(database)
def startSession(cursor:sqlite3.Cursor,connection:sqlite3.Connection,username,password):
    # Query the database for the provided username and password
    cursor.execute("SELECT username,password FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()

    
    # If user exists, return True (valid credentials), otherwise return False
    if user:
        correctPassword = bcrypt.checkpw(password.encode('utf-8'), user[1])
        if correctPassword:
            return True
        else:
            return False
    else:
        return False
    
@app.route('/users', methods=["POST","DELETE","GET","PUT"])
def users():
    if request.method == "POST":
        # Signup a new user
        jsonData = request.get_json()
        if validateData(["username","password","role","firstname","middlename","lastname"],jsonData) == False:
            response = responseJson(400,"Incorrect parameters sent")
            return response

        jsonData["password"] = hashPassword(jsonData["password"])
        if insertUser(jsonData):
            return "",200
        else:
            response = responseJson(400,"User already exists")
            return response


    elif request.method == "DELETE":
        # Delete an existing user
        jsonData = request.get_json()
        if validateData(["currentUserId","userId"],jsonData) == False:
            response = responseJson(400,"Incorrect parameters sent")
            return response
        
        # Checks if the current user is an admin
        if not checkAdmin(jsonData["currentUserId"]):
            response = responseJson(401,"Unauthorized access")
            return response

        # Checks if the user exists and deletes it
        if deleteUser(jsonData["userId"]):
            return "",200
        else:
            response = responseJson(400,"User doesn't exist")
            return response
        
    elif request.method == "GET":
        # Get data for a given user
        id = request.args.get("id")
        if not id:
            response = responseJson(400,"Incorrect parameters sent")
            return response
        
        user = getUser(id)
        if user != None:
            # Success
            response = jsonify(user)
            response.status_code = 200
            return response
        else:
            # User not found
            response = responseJson(404,"User doesn't exist")
            return response
        
    elif request.method == "PUT":
        # Edit existing user
        jsonData = request.get_json()

        if validateData(["currentUserId","userId","username","password","role","firstname","middlename","lastname","points"],jsonData) == False:
            response = responseJson(400,"Incorrect parameters sent")
            return response

        # Checks if the current user is an admin
        if not checkAdmin(jsonData["currentUserId"]):
            response = responseJson(401,"Unauthorized access")
            return response

        jsonData["password"] = hashPassword(jsonData["password"])
        if editUser(jsonData):
            return "",200
        else:
            response = responseJson(400,"User doesn't exist")
            return response
        
# Function to check whether the user exists yet, if it doesn't then it registers the new user
@query(database)
def insertUser(cursor:sqlite3.Cursor,connection:sqlite3.Connection,data:dict):
    # Checks wheter the user exists
    cursor.execute("SELECT * FROM users WHERE username = ?", (data["username"],))
    user = cursor.fetchone()
    if user:
        return False
    
    #Check if points where passed, if not default to 0
    if "points" not in data:
        data["points"] = 0

    # Insert user
    cursor.execute("INSERT INTO users (username, password, role, firstname, middlename, lastname, points) VALUES (?, ?, ?, ?, ?, ?, ?)", (data["username"], data["password"], data["role"], data["firstname"], data["middlename"], data["lastname"], data["points"]))
    
    # Commit the transaction
    connection.commit()
    
    return True

# Function to delete user if it exists
@query(database)
def deleteUser(cursor:sqlite3.Cursor,connection:sqlite3.Connection,id:str):
    # Checks wheter the user exists
    cursor.execute("SELECT * FROM users WHERE id = ?", (id,))
    user = cursor.fetchone()
    if not user:
        return False

    # Borrar al usuario indicado
    cursor.execute("DELETE FROM users WHERE id = ?", (id,))
    connection.commit()
    return True

# Function that returns user based on id
@query(database)
def getUser(cursor:sqlite3.Cursor,connection:sqlite3.Connection,id:str):
    # Retrieve user(will be None in case it's not found)
    data = cursor.execute("SELECT id,role,firstname,middlename,lastname,username,points FROM users WHERE id = ?", (id,))
    row = data.fetchone()
    if not row:
        return None
    
    # Add keys to the values returned 
    user = {}
    for id,column in enumerate(data.description):
        user[column[0]] = row[id]
        
    return user

# Function to check whether the user exists and edits it
@query(database)
def editUser(cursor:sqlite3.Cursor,connection:sqlite3.Connection,data:dict):
    # Checks wheter the user exists
    cursor.execute("SELECT * FROM users WHERE id = ?", (data["userId"],))
    user = cursor.fetchone()
    if not user:
        return False

    # Insert user
    cursor.execute("UPDATE users SET username = ?, password = ?, role = ?, firstname = ?, middlename = ?, lastname = ?, points = ? WHERE id = ?",
                    (data["username"], data["password"], data["role"], data["firstname"], data["middlename"], data["lastname"], data["points"],data["userId"]))
    
    # Commit the transaction
    connection.commit()
    return True

@app.route('/proposals', methods=["POST","PUT","GET"])
def proposals():
    if request.method == "POST":
        # Create a new proposal
        jsonData = request.get_json()
        if validateData(["title","description","currentSituation","area","status","type","feedback","usersId"],jsonData) == False:
            response = responseJson(400,"Incorrect parameters sent")
            return response

        if createProposal(jsonData):
            return "",200
        else:
            response = responseJson(400,"User not found")
            return response

    elif request.method == "PUT":
        # Edit an existing proposal
        jsonData = request.get_json()
        if validateData(["currentUserId","proposalId","title","description","currentSituation","area","status","type","feedback","usersId"],jsonData) == False:
            response = responseJson(400,"Incorrect parameters sent")
            return response
        
        result = editProposal(jsonData)
        
        if result == 0:
            response = responseJson(400,"User not found")
            return response
        elif result == 1:
            response = responseJson(401,"User not authorized to edit")
            return response
        elif result == 2:
            response = responseJson(404,"Proposal not found")
            return response
        else:
            return "",200
        

    elif request.method == "GET":   
        # Get data for a given user
        id = request.args.get("id")
        if not id:
            response = responseJson(400,"Incorrect parameters sent")
            return response
        
        proposal = getProposal(id)
        if proposal != None:
            # Success
            response = jsonify(proposal)
            response.status_code = 200
            return response
        else:
            # Proposal not found
            response = responseJson(404,"Proposal not found")
            return response

# Function to create a proposal, returns true if succesful and false if unsuccesful
@query(database)
def createProposal(cursor:sqlite3.Cursor,connection:sqlite3.Connection,data:dict):
    #check if it breaks when deleting and adding new proposals
    # Insert proposal
    cursor.execute("INSERT INTO proposals (title,current_situation, area, status, proposal, type, feedback) VALUES (?,?, ?, ?, ?, ?, ?)",
                    (data["title"], data["currentSituation"], data["area"], data["status"], data["description"], data["type"], data["feedback"]))
    
    proposalId = cursor.lastrowid

    # Insert into userProposals
    for id in data["usersId"]:
        data = cursor.execute("SELECT * FROM users WHERE id = ?", (id,))
        row = data.fetchone()
        if not row:
            connection.rollback()
            return False
        cursor.execute("INSERT INTO userProposals (user_id, proposal_id) VALUES (?, ?)",(id,proposalId))

    # Commit the transaction
    connection.commit()
    return True

# Function to edit an existing proposal, returns 0 if succesful. Other numbers are different errors
@query(database)
def editProposal(cursor:sqlite3.Cursor,connection:sqlite3.Connection,data:dict):
    # Checks wheter the proposal exists
    cursor.execute("SELECT * FROM proposals WHERE id = ?", (data["proposalId"],))
    proposal = cursor.fetchone()
    if not proposal:
        return 2

    # Edit proposal
    cursor.execute("UPDATE proposals SET current_situation = ?, area = ?, status = ?, proposal = ?, type = ? WHERE id = ?",
                    (data["currentSituation"], data["area"], data["status"], data["description"], data["type"], data["proposalId"]))
        
    cursor.execute("DELETE FROM userProposals WHERE proposal_id = ?",(data["proposalId"],))
    # Insert into userProposals
    for id in data["usersId"]:
        result = cursor.execute("SELECT * FROM users WHERE id = ?", (id,))
        row = result.fetchone()
        if not row:
            connection.rollback()
            return 0
        cursor.execute("INSERT INTO userProposals (user_id, proposal_id) VALUES (?, ?)",(id,data["proposalId"]))
    
    # Checks whether the user is an admin
    cursor.execute("SELECT role FROM users WHERE id = ?",(data["currentUserId"],))
    row = result.fetchone()
    if row:
        connection.commit()
        return 3
    # Checks whether the user editing is one of the people who suggested it
    cursor.execute("SELECT user_id FROM userProposals WHERE proposal_id = ?",(data["proposalId"],))
    for i in cursor:
        if i[0] == data["currentUserId"]:
            connection.commit()
            return 3   
         
    connection.rollback()
    return 1

# Function to retrieve a proposal, return None if it fails
@query(database)
def getProposal(cursor:sqlite3.Cursor,connection:sqlite3.Connection,id):
    # Retrieve proposal(will be None in case it's not found)
    data = cursor.execute("SELECT id,title,current_situation,area,status,proposal,type,feedback FROM proposals WHERE id = ?", (id,))
    row = data.fetchone()
    if not row:
        return None
    
    # Add keys to the values returned 
    proposal = {}
    for i,column in enumerate(data.description):
        proposal[column[0]] = row[i]

    # Append all the users involved
    cursor.execute("SELECT user_id FROM userProposals WHERE proposal_id = ?",(id,))
    users = []
    for i in cursor:
        print(i)
        users.append(i[0])
    proposal["usersId"] = users
            
    return proposal

# Order endpoints
@app.route("/orders", methods=["GET", "POST", "PUT"]) 
def orders():
    if request.method == "POST":
        # Create a new order
        jsonData = request.get_json()
        if validateData(["userId","productId","quantity","orderStatus","orderDate","total"],jsonData) == False:
            response = responseJson(400,"Incorrect parameters sent")
            return response
        if createOrder(jsonData):
            return "",200
        else:
            response = responseJson(400,"Could not create order")
            return response

    elif request.method == "PUT":
        # Edit an existing order
        if updateOrder(request.get_json()):
            return "",200
        else:
            response = responseJson(404,"Order not found")
            return response
    elif request.method == "GET":
        if request.args.get("id"):
            response = getOrderById(request.args.get("id"))
            if response != None:
                response = jsonify(response)
                response.status_code = 200
                return response
            else:
                # Order not found
                response = responseJson(404,"Order not found")
                return response
        else:    
            response = getOrders()
            if response != None:
                response = jsonify(response)
                response.status_code = 200
                return response
            else:
                # Order not found
                response = responseJson(404,"No orders found")
                return response
@query(database)
def createOrder(cursor:sqlite3.Cursor,connection:sqlite3.Connection,data:dict):
    try:
    # Insert order
        cursor.execute("INSERT INTO orders (user_id, product_id, quantity, order_status, order_date, total) VALUES (?, ?, ?, ?, ?, ?)", (data["uderId"], data["productId"], data["quantity"], data["orderStatus"], data["orderDate"], data["total"]) )
        connection.commit()
        return True
    except Exception as e:
        print(e)
        connection.rollback()
        return False
    
@query(database)
def getOrders(cursor:sqlite3.Cursor,connection:sqlite3.Connection):
    # Retrieve order(will be None in case it's not found)
    try:

        data = cursor.execute("SELECT * FROM orders;")
        row = data.fetchall()
        if not row:
            return None
        
        # Add keys to the values returned 
        orders = {}
        for i,column in enumerate(data.description):
            orders[column[0]] = row[i]

                
        return orders
    except Exception as e:
        print(e)
        return None

@query(database)
def getOrderById(cursor:sqlite3.Cursor,connection:sqlite3.Connection, id:int):
    try:
        # Retrieve order(will be None in case it's not found)
        data = cursor.execute("SELECT * FROM orders WHERE id = ?;", (id,))
        row = data.fetchone()
        if not row:
            return None
        
        # Add keys to the values returned 
        orders = {}
        for i,column in enumerate(data.description):
            orders[column[0]] = row[i]

                
        return orders
    except Exception as e:
        print(e)
        return None

@query(database)
def updateOrder(cursor:sqlite3.Cursor,connection:sqlite3.Connection,data:dict):
    try:

        # Checks wheter the order exists
        cursor.execute("SELECT * FROM orders WHERE id = ?", (data["orderId"],))
        order = cursor.fetchone()
        if not order:
            return False
        # Update order
        cursor.execute("UPDATE orders SET user_id = ?, product_id = ?, quantity = ?, order_status = ?, order_date = ?, total = ? WHERE id = ?",
                        (data["uderId"], data["productId"], data["quantity"], data["orderStatus"], data["orderDate"], data["total"], data["orderId"]))
        connection.commit()
        return True
    except Exception as e:
        print(e)
        connection.rollback()
        return False
# End of order endpoints

# Product endpoints
@app.route("/products", methods=["GET", "POST", "PUT", "DELETE"])
def products():
    if request.method == "POST":
        # Create a new order
        jsonData = request.get_json()
        print(request.get_json())
        if validateData(["name", "description", "price", "image"], jsonData) == False:
            response = responseJson(400,"Incorrect parameters sent")
            return response
        if createProduct(jsonData):
            return "",200
        else:
            response = responseJson(400,"Could not create product ")
            return response
        

    elif request.method == "PUT":   
        # Edit an existing order
        if updateOrder(request.get_json()):
            return "",200
        else:
            response = responseJson(404,"Product not found")
            return response



    elif request.method == "GET":
        if request.args.get("id"):

            response = getProductById(request.args.get("id"))

            if response != None:
                response = jsonify(response)  
                return response  
            else:
                # Product not found
                response = responseJson(404,"Product not found")
                return response
        else:
            response = getProducts()
            if response != None:
                response = jsonify(response)
                response.status_code = 200
                return response
            else:
                # Product not found
                response = responseJson(404,"No Products found")
                return response
            
    elif request.method == "DELETE":
        if deleteProduct(request.get_json()):
            return "",200
        else:
            response = responseJson(404,"Product not found")
            return response

@query(database)
def createProduct(cursor:sqlite3.Cursor,connection:sqlite3.Connection,data:dict):
    try:

        print(data)
    # Insert product
        cursor.execute("INSERT INTO products (name, description, price, image) VALUES (?, ?, ?, ?)", (data["name"], data["description"], data["price"], data["image"]) )
        connection.commit()
        return True
    except Exception as e:
        print(e)
        connection.rollback()
        return False

@query(database)
def getProducts(cursor:sqlite3.Cursor,connection:sqlite3.Connection):
    # Retrieve product(will be None in case it's not found)
    data = cursor.execute("SELECT * FROM products;")
    row = data.fetchall()
    if not row:
        return None
    products = []
    # Add keys to the values returned 
    for product in row:
        product = {
            "id": product[0],
            "name": product[1],
            "description": product[2],
            "price": product[3],
            "image": product[4]
        }
        products.append(product)
    return products

@query(database)
def getProductById(cursor:sqlite3.Cursor,connection:sqlite3.Connection, id:int):
    try:

        # Retrieve product(will be None in case it's not found)
        data = cursor.execute("SELECT * FROM products WHERE id = ?;", (id,))
        row = data.fetchone()
        if not row:
            return None

        # Add keys to the values returned 
        product = {}
        for i,column in enumerate(data.description):
            product[column[0]] = row[i]

        return product
    
    except Exception as e:
        print(e)
        return None

@query(database)
def updateProduct(cursor:sqlite3.Cursor,connection:sqlite3.Connection,data:dict):
    try:

        # Checks wheter the product exists
        cursor.execute("SELECT * FROM products WHERE id = ?", (data["id"],))
        product = cursor.fetchone()
        if not product:
            return False
        # Update product
        cursor.execute("UPDATE products SET name = ?, description = ?, price = ?, image = ? WHERE id = ?",
                        (data["name"], data["description"], data["price"], data["image"], data["id"]))
        connection.commit()
        return True
    except Exception as e:
        print(e)
        connection.rollback()
        return False
    
@query(database)
def deleteProduct(cursor:sqlite3.Cursor,connection:sqlite3.Connection,data:dict):
    try:
        cursor.execute("SELECT * FROM products WHERE id = ?", (data["id"],))
        product = cursor.fetchone()
        if not product:
            return False
        # Delete product
        cursor.execute("DELETE FROM products WHERE id = ?", (data["id"],))
        connection.commit()
        return True
    except Exception as e:
        print(e)
        connection.rollback()
        return False
# End of product endpoints