from flask import Blueprint, request
from app.utils import *

bp = Blueprint('users',__name__, url_prefix='/users')

@bp.route('', methods=["POST","DELETE","GET","PUT"])
def users():
    if request.method == "POST":
        # Signup a new user
        jsonData = request.get_json()
        if validateData(["username","password","role","firstname","middlename","lastname","email","area"],jsonData) == False:
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
        if validateData(["currentUser","deleteUser"],jsonData) == False:
            response = responseJson(400,"Incorrect parameters sent")
            return response
        
        # Checks if the current user is an admin
        if not checkAdmin(jsonData["currentUser"]):
            response = responseJson(401,"Unauthorized access")
            return response

        # Checks if the user exists and deletes it
        if deleteUser(jsonData["deleteUser"]):
            return "",200
        else:
            response = responseJson(400,"User doesn't exist")
            return response
        
    elif request.method == "GET":
        # Get data for a given user
        username = request.args.get("username")
        role = request.args.get("role")
        area = request.args.get("area")
        if username != None:
            # Looking for a single user
            user = getUsers(["username",username])
            if user:
                # Success
                response = jsonify(user)
                response.status_code = 200
                return response
            else:
                # User not found
                response = responseJson(404,"User doesn't exist")
                return response
        elif role != None:
            # Looking for a particular role
            users = getUsers(["role",role])
            response = jsonify(users)
            response.status_code = 200
            return response
        elif area != None:
            # Looking for a particular area
            users = getUsers(["area",area])
            response = jsonify(users)
            response.status_code = 200
            return response
        elif not any(request.args.values()):
            # Looking for all users
            users = getUsers(["1",1])
            response = jsonify(users)
            response.status_code = 200
            return response
        else:
            # Incorrect parameters
            response = responseJson(400,"Incorrect parameters sent")
            return response
        
    elif request.method == "PUT":
        # Edit existing user
        jsonData = request.get_json()

        if validateData(["currentUser","username","role","firstname","middlename","lastname","email","area"],jsonData) == False:
            response = responseJson(400,"Incorrect parameters sent")
            return response

        # Checks if the current user is an admin
        if not checkAdmin(jsonData["currentUser"]):
            response = responseJson(401,"Unauthorized access")
            return response

        if editUser(jsonData):
            return "",200
        else:
            response = responseJson(400,"User doesn't exist")
            return response
        
# Function to check whether the user exists yet, if it doesn't then it registers the new user
@query(database)
def insertUser(cursor:sqlite3.Cursor,connection:sqlite3.Connection,data:dict):
    # Checks whether the user exists
    cursor.execute("SELECT * FROM users WHERE username = ?", (data["username"],))
    user = cursor.fetchone()
    if user:
        return False
    
    #Check if points where passed, if not default to 0
    if "points" not in data:
        data["points"] = 0

    # Insert user
    cursor.execute("INSERT INTO users (username, password, role, firstName, middleName, lastName, email, points, area) VALUES (?, ?, ?, ?, ?, ?, ?, ?,?)", 
                   (data["username"], data["password"], data["role"], data["firstname"], data["middlename"], data["lastname"], data["email"], data["points"], data["area"]))
    
    send_email(data["email"], { "name": data["firstname"], "email": data["email"], "username": data["username"] }, "user_signup_confirmation")
    # Commit the transaction
    connection.commit()
    
    return True

# Function to delete user if it exists
@query(database)
def deleteUser(cursor:sqlite3.Cursor,connection:sqlite3.Connection,username:str):
    # Checks whether the user exists
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    if not user:
        return False

    # Borrar al usuario indicado
    cursor.execute("DELETE FROM users WHERE username = ?", (username,))
    connection.commit()
    return True

# Function that returns user based on id
@query(database)
def getUsers(cursor:sqlite3.Cursor,connection:sqlite3.Connection,condition):
    # Retrieve user(will be None in case it's not found)
    data = cursor.execute("SELECT role,firstName,middleName,lastName,username,email,points,area FROM users WHERE " + condition[0] + " = ?", (condition[1],))
    users = []
    columns = data.description
    for i in data.fetchall():
        # Add keys to the values returned 
        user = {}
        for id,column in enumerate(columns):
            user[column[0]] = i[id]

        # Retrieve all proposals that have to do with the user
        result = cursor.execute("SELECT proposalId FROM UserProposal WHERE user = ?",(user["username"],))
        user["proposals"] = []
        for proposal in result.fetchall():
            user["proposals"].append(proposal[0])

        users.append(user)
    if condition[0] == "username" and users:
        return users[0]
    return users

# Function to check whether the user exists and edits it
@query(database)
def editUser(cursor:sqlite3.Cursor,connection:sqlite3.Connection,data:dict):
    # Checks whether the user exists
    cursor.execute("SELECT password, firstname, middlename, lastname, email FROM users WHERE username = ?", (data["username"],))
    user = cursor.fetchone()
    if not user:
        return False

    # Check if points where passed, if not default to 0
    if "points" not in data:
        data["points"] = 0
    """
        user_data_change_confirmation Returns a user data change confirmation email.
            email_content: {
                "name": User name,
                "previousName": Previous user name,
                "email": New user email,
                "previousEmail": Previous user email
            }
    """
    # If user data has changed
    if user[1] != data["firstname"] or user[2] != data["middlename"] or user[3] != data["lastname"] or user[4] != data["email"]:
        send_email(data["email"], 
            { 
                "name": data["firstname"] + " " + data["middlename"] + " " + data["lastname"], 
                "previousName": user[1] + " " + user[2] + " " + user[3], 
                "email": data["email"], 
                "previousEmail": user[4] 
            }, 
            "user_data_change_confirmation"
        )

    # Check if password is passed, if not make it the past one
    if "password" in data:
        data["password"] = hashPassword(data["password"])
        send_email(data["email"], { "name": data["firstname"] }, "password_reset_confirmation")
    else:
        data["password"] = user[0]
    # Insert user
    cursor.execute("UPDATE users SET password = ?, role = ?, firstname = ?, middlename = ?, lastname = ?, points = ?, email = ?, area = ? WHERE username = ?",
                    (data["password"], data["role"], data["firstname"], data["middlename"], data["lastname"], data["points"], data["email"], data["area"], data["username"]))
    
    # Commit the transaction
    connection.commit()
    return True
