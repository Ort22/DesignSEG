from flask import Blueprint, request
from app.utils import *

bp = Blueprint('orders',__name__, url_prefix='/orders')


# Order endpoints
@bp.route("/", methods=["GET", "POST", "PUT"]) 
def orders():
    if request.method == "GET":
        if len(request.args) > 0:
            if validateData(["id"],request.args) == False:
                response = responseJson(400,"Incorrect parameters sent")
                return response
            
            # Get order by id
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
    elif request.method == "POST":
        # Create a new order
        jsonData = request.get_json()
        if validateData(["username","productId","quantity","orderStatus","orderDate","total"],jsonData) == False:
            response = responseJson(400,"Incorrect parameters sent")
            return response
        
        response = createOrder(jsonData)

        return responseJson(response["status"], response["result"])

    elif request.method == "PUT":
        # Edit an existing order
        if validateData(["currentUser","orderId","username","orderStatus","orderDate","total","productId","quantity"],request.get_json()) == False:
            response = responseJson(400,"Incorrect parameters sent")
            return response
        response = updateOrder(request.get_json())
        return responseJson(response["status"], response["result"])
    
@query(database)
def createOrder(cursor:sqlite3.Cursor,connection:sqlite3.Connection,data:dict):
    try:
    # Insert order
        cursor.execute("SELECT * FROM users WHERE username = ?", (data["username"],))
        user = cursor.fetchone()
        if not user:
            return { "status": 404, "result": "User not Found"}

        cursor.execute("SELECT * FROM products WHERE id = ?", (data["productId"],))
        product = cursor.fetchone()
        if not product:
            return { "status": 404, "result": "Product not Found"}
        
        elif user[8] < data["total"]:
            return { "status": 400, "result": "Not enough points"}

        # Insert order and update user points
        cursor.execute("INSERT INTO orders (username, productId, quantity, orderStatus, orderDate, total) VALUES (?, ?, ?, ?, ?, ?)", (data["username"], data["productId"], data["quantity"], data["orderStatus"], data["orderDate"], data["total"]) )
        cursor.execute("UPDATE users SET points = points - ? WHERE username = ?", (data["total"], data["username"]))
        connection.commit()
        return { "status": 200, "result": "Order created"}
    except Exception as e:
        print(e)
        connection.rollback()
        return { "status": 500, "result": e}
    
@query(database)
def getOrders(cursor:sqlite3.Cursor,connection:sqlite3.Connection):
    # Retrieve order(will be None in case it's not found)
    try:
        data = cursor.execute("SELECT * FROM Orders;")
        row = data.fetchall()
        if not row:
            return None
        orders = []
        # Add keys to the values returned 
        for order in row:
            order = {
                "id": order[0],
                "userId": order[1],
                "productId": order[2],
                "quantity": order[3],
                "orderStatus": order[4],
                "orderDate": order[5],
                "total": order[6]
            }
            orders.append(order)
        return orders
    except Exception as e:
        print(e)
        return None

@query(database)
def getOrderById(cursor:sqlite3.Cursor,connection:sqlite3.Connection, id:int):
    try:
        # Retrieve order(will be None in case it's not found)
        data = cursor.execute("SELECT * FROM orders, products WHERE orders.id = ? AND products.id = orders.productId;", (id,))




        row = data.fetchall()
        print(row)
        if not row:
            return None
        # Add keys to the values returned 
        orders = []
        # Add keys to the values returned 
        for order in row:
            product = {
                "id": order[7],
                "name": order[8],
                "description": order[9],
                "price": order[10],
                "image": order[11]
            }
            order = {
                "id": order[0],
                "userId": order[1],
                "productId": order[2],
                "quantity": order[3],
                "orderStatus": order[4],
                "orderDate": order[5],
                "total": order[6],
                "product": product
            }
            orders.append(order)
        return orders
    except Exception as e:
        print(e)
        return None

@query(database)
def updateOrder(cursor:sqlite3.Cursor,connection:sqlite3.Connection,data:dict):
    try:

        # Checks whether the order exists
        cursor.execute("SELECT * FROM orders WHERE id = ?;", (data["orderId"],))
        order = cursor.fetchone()
        if not order:
            return {"status": 400, "result": "Order Not Found"}
        
        # Checks whether the user exists and is an admin and has order edit privileges
        cursor.execute("SELECT role FROM users WHERE username = ?", (data["currentUser"],))
        user = cursor.fetchone()
        print(user[0])
        if not user:
            return {"status": 404, "result": "User not Found"}
        if str(user[0]) != "admin" and str(user[0]) != "VSE":
            return {"status": 403, "result": "User has no order edit privileges"}

        # Checks whether the product exists
        cursor.execute("SELECT * FROM products WHERE id = ?", (data["productId"],))
        product = cursor.fetchone()
        if not product:
            return {"status": 404, "result": "Product not Found"}


        # Update order
        cursor.execute("UPDATE orders SET username = ?, productId = ?, quantity = ?, orderStatus = ?, orderDate = ?, total = ? WHERE id = ?",
                        (data["username"], data["productId"], data["quantity"], data["orderStatus"], data["orderDate"], data["total"], data["orderId"]))
        connection.commit()
        return {"status": 200, "result": "Order updated"}
    except Exception as e:
        print(e)
        connection.rollback()
        return False
# End of order endpoints
