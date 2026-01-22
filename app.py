from flask import make_response, request
from flask_restful import Resource
from sqlalchemy import asc
import random

from config import app, db, api
from models import *

# GET request
# Fields
# -- password | Encrypted user password.
# -- username | Accessor's username.
class CheckSession(Resource):
    def get(self):
        # Set the scope of allowed users to call this function
        allowed_user_query = User.query.filter(User.isbanned == False)
        # Get the parameters of this request
        json = request.get_json()
        # Obtain the username from the request
        username = json.get('username', "")
        # Obtain the password from the request
        password = json.get('password', "")
        # Obtain the user by the password token and username
        user:User = allowed_user_query.filter((User._password_hash == password) and (User.username == username)).first()
        # Check if the user is authorized
        if not user:
            return make_response({'error': "Unauthorized: you must be logged in to make that request"}, 401)
        # Return the secret data of the user. This data is accessed on front end for user authentication using sessions.
        return make_response(user.private_dict(), 200)
# Add CheckSession method to the routing system. 
api.add_resource(CheckSession, '/check_session', endpoint='check_session')

# POST request
# Fields
# -- password | Decrypted user password.
# -- username | Accessor's username.
class SignUp(Resource):
    def post(self):
        # Get the parameters of this request
        json = request.get_json()
        # Obtain the username from the request
        username = json.get('username', "").lower().strip()
        # Check if the username is long enough
        if(len(username) < 5):
            return make_response({'error': "Username is too short"}, 422)
        # Check if the username recurrs
        user = User.query.filter(User.username == username).first()
        if(user):
            return make_response({'error': "Username is already taken"}, 422)
        # Obtain the password from the request
        password = json.get('password', "").strip()
        if(len(password) < 8):
            return make_response({'error': "Password is too short"}, 422)
        if(len(password) > 128):
            return make_response({'error': "Password is too long"}, 422)
        # Obtain the real name from the request
        name = json.get('name', "")
        # Check if the real name exists
        if(len(name) == 0):
            return make_response({'error': "Real name is not given"}, 422)
        # Create a new instant of user
        user = User(
            username=username,
            name=name,
        )
        # Encrypt the password to password_hash
        user.password_hash = password
        # Perform CREATE operation to the user instant in the database
        db.session.add(user)
        # Commit all database changes
        db.session.commit()
        # Return the secret data of the user. This data is accessed on front end for user authentication using sessions.
        return make_response(user.private_dict(), 201)
# Add Signup method to the routing system.   
api.add_resource(SignUp, '/signup', endpoint='signup')

# POST request
# Fields
# -- password | Decrypted user password.
# -- username | Accessor's username.
class Login(Resource):
    def post(self):
        # Get the parameters of this request
        json = request.get_json()
        # Obtain the username from the request
        username = json.get('username', "")
        # Obtain the password from the request
        password = json.get('password', "")
        # Search if there's a user with a same username
        user = User.query.filter(User.username == username).first()
        # Validate if a user with a same username doesn't exist
        if(not user):
            return make_response({'error': "User not found"}, 404)
        if(user.isbanned):
            return make_response({'error': "Banned"}, 404)
        # Users are checked if they're authenticated by using the password
        if user.authenticate(password):
            # Return the secret data of the user. This data is accessed on front end for user authentication using sessions.
            return make_response(user.private_dict(), 200)
        else:
            # The password is incorrect
            return make_response({'error': "Incorrect password or username"}, 402)
# Add Login method to the routing system.   
api.add_resource(Login, '/login', endpoint='login')

# POST request
# Fields
# -- password | Encrypted user password.
# -- username | Accessor's username.
# -- opponent | Opponent's username.
# -- result | Result of the match. This value can only be from "Win", "Lose" or "Draw".
class RequestMatch(Resource):
    def post(self):
        # Set the scope of allowed users to call this function
        allowed_user_query = User.query.filter((User.isbanned == False) & (User.isactivated == True))
        # Get the parameters of this request
        json = request.get_json()
        # Obtain the username from the request
        username = json.get('username', "")
        # Obtain the password from the request
        password = json.get('password', "")
        # Obtain the first user by the password token and username
        user1:User = allowed_user_query.filter((User._password_hash == password) & (User.username == username)).first()
        # Validate if the password token and username is correct
        if(not user1):
            return make_response({'error': "Unauthorized: you must be logged in to make that request"}, 401)
        # Obtain the password from the request
        opponent = json.get('opponent', "")
        # Obtain the second user by the username
        user2:User = User.query.filter((User.username == opponent) & (User.isactivated == True)).first()
        # Validate if the username is correct
        if(not user2):
            return make_response({'error': "Incorrect password or username"}, 402)
        # Check if both users are same
        if(user1 == user2):
            return make_response({'error': "You cannot request match yourself"}, 422)
        # Check if result can be obtained
        result = json.get("result", "")
        # Validate result value
        if (not (result in ["Draw", "Win", "Lose"])):
            return make_response({'error': "Incorrect field for match result"}, 422)
        # Create a new MatchRequest instance
        match_request = MatchRequest(
            user1_id=user1.id,
            user2_id=user2.id,
            result=json['result']
        )
        # Perform CREAT for the MatchRequest object in the server
        db.session.add(match_request)
        # Commit the operations
        db.session.commit()
        # Return the public data of the match request. Parameter user1.id is used to identify if which user is accessing the data
        return make_response(match_request.public_dict(user1.id), 200)
# Add RequestMatch method to the routing system.       
api.add_resource(RequestMatch, '/request_match', endpoint='request_match')

# GET request
# Fields
# -- password | Encrypted user password.
# -- username | Accessor's username.
class Matchmaking(Resource):
    def get(self):
        # Set the scope of allowed users to call this function
        allowed_user_query = User.query.filter((User.isbanned == False))
        # Get the parameters of this request
        json = request.get_json()
        # Obtain the username from the request
        username = json.get('username', "")
        # Obtain the password from the request
        password = json.get('password', "")
        # Find a user from the password token. If this fail, the user has not been authenticated.
        user:User = allowed_user_query.filter((User._password_hash == password) & (User.username == username)).first()
        # Check if the user is authorized
        if not user:
            return make_response({'error': "Unauthorized: you must be logged in to make that request"}, 401)
        #-#-# Search through opponents. Make sure that at leaast 3 opponents are in range. Set timeout to 1000 #-#-#
        # If a suitable opponent has been found
        found_opponent = False
        # Increment in the elo range of matchmaking each loop 
        increment = 40
        # How much loops there will be before giving up
        timeout = 20
        # Variable to keep track of the number of loops
        count = 0
        # Set the scope of allowed users be returned in this function
        allowed_user_query = User.query.filter((User.isactivated == True) & (User.isbanned == False) & (User.ishidden == False) & (User.id != user.id))
        while(not found_opponent):
            # List of all the suitable opponents inside the elo range
            opponents = allowed_user_query.filter((-40-increment*count < User.elo - user.elo) & (User.elo - user.elo < 40+increment*count)).all()
            # If opponents are not found, return the whole list. This shouldn't be an issue.
            if(count > timeout):
                opponents = allowed_user_query.all()
                found_opponent = True
            # Stop the process if more than three players are found
            if(len(opponents) >= 3):
                found_opponent = True
            # Increment the counter
            count += 1
        # Get a random opponent from the list of suitable opponent
        opponent = random.choice(opponents)
        # Return the public data of the opponent
        return make_response(opponent.public_dict(), 200)
# Add Matchmaking method to the routing system.
api.add_resource(Matchmaking, '/matchmaking', endpoint='matchmaking')

# GET request
# Fields
# -- password | Encrypted user password.
# -- username | Accessor's username.
class GetMatchRequest(Resource):
    def get(self):
        # Set the scope of allowed users to call this function
        allowed_user_query = User.query.filter((User.isbanned == False))
        # Get the parameters of this request
        json = request.get_json()
        # Obtain the username from the request
        username = json.get('username', "")
        # Obtain the password from the request
        password = json.get('password', "")
        # Find a user from the password token. If this fail, the user has not been authenticated.
        user:User = allowed_user_query.filter((User._password_hash == password) & (User.username == username)).first()
        # Check if the user is authorized
        if not user:
            return make_response({'error': "Unauthorized: you must be logged in to make that request"}, 401)
        # Find all match requests with the user as user2
        match_request_query = MatchRequest.query.filter(MatchRequest.user2_id == user.id)
        match_request = match_request_query.order_by(asc(MatchRequest.request_time)).first()
        if(match_request):
            # Return the list of all match requests with the user as user2
            return make_response({'match_request': match_request.public_dict(user.id)}, 200)
        else:
            return make_response({'message': "No requests exist"}, 200)
# Add GetMatchRequests method to the routing system. 
api.add_resource(GetMatchRequest, '/get_match_request', endpoint='get_match_request')

# GET request
# Fields
# -- password | Encrypted user password.
# -- username | Accessor's username.
class GetMatches(Resource):
    def get(self):
        # Set the scope of allowed users to call this function
        allowed_user_query = User.query.filter((User.isbanned == False))
        # Get the parameters of this request
        json = request.get_json()
        # Obtain the username from the request
        username = json.get('username', "")
        # Obtain the password from the request
        password = json.get('password', "")
        # Find a user from the password token. If this fail, the user has not been authenticated.
        user:User = allowed_user_query.filter((User._password_hash == password) & (User.username == username)).first()
        # Check if the user is authorized
        if not user:
            return make_response({'error': "Unauthorized: you must be logged in to make that request"}, 401)
        # Get all matches with the user as either user1 or user2
        matches = Match.query.filter((Match.user2_id == user.id) | (Match.user1_id == user.id)).all()
        # Convert each class to a dictionary by using public_dict
        for i in range(len(matches)):
            matches[i] = matches[i].public_dict(user.id)
        # Return the list of all matches consisting the user as a public data
        return make_response(matches, 200)
# Add GetMatches method to the routing system. 
api.add_resource(GetMatches, '/get_matches', endpoint='get_matches')

# GET request
# Fields
# -- password | Encrypted user password.
# -- username | Accessor's username.
# -- match_request_id | ID of the match request to be accepted.
class AcceptMatchRequest(Resource):
    def post(self):
        # Set the scope of allowed users to call this function
        allowed_user_query = User.query.filter((User.isbanned == False) & (User.isactivated == True))
        # Get the parameters of this request
        json = request.get_json()
        # Obtain the username from the request
        username = json.get('username', "")
        # Obtain the password from the request
        password = json.get('password', "")
        # Find a user from the password token. If this fail, the user has not been authenticated.
        user:User = allowed_user_query.filter((User._password_hash == password) & (User.username == username)).first()
        # Check if the user is authorized
        if not user:
            return make_response({'error': "Unauthorized: you must be logged in to make that request"}, 401)
        # Obtain the match request id from the request
        match_request_id = json.get('match_request_id', "")
        # Find a match_request from id
        match_request:MatchRequest = MatchRequest.query.filter(MatchRequest.id == match_request_id).first()
        # Validate if the match_request exists
        if not match_request:
            return make_response({'error': "Cannot find the match"}, 422)
        if((not user.isadmin) and (user.id != match_request.user2_id)):
            return make_response({'error': "You don't have the permission to make this request"}, 422)
        # Create a match instance
        match = Match(
            user1_id = match_request.user1_id,
            user2_id = match_request.user2_id,
            result = match_request.result,
            time = match_request.request_time,
        )
        # Update the elo of both users
        match.record()
        # Perform CREATE operation for the new match instance in the database
        db.session.add(match)
        # Perform DELETE operation for the match request
        db.session.delete(match_request)
        # Commit database changes
        db.session.commit()
        # Return the public data of the match
        return make_response(match.public_dict(match_request.user2_id), 200)
# Add AcceptMatchRequest method to the routing system.
api.add_resource(AcceptMatchRequest, '/accept_match_request', endpoint='accept_match_request')

# GET request
# Fields
# -- password | Encrypted user password.
# -- username | Accessor's username.
# -- match_request_id | ID of the match request to be rejected.
class RejectMatchRequest(Resource):
    def post(self):
        # Set the scope of allowed users to call this function
        allowed_user_query = User.query.filter((User.isbanned == False) & (User.isactivated == True))
        # Get the parameters of this request
        json = request.get_json()
        # Obtain the username from the request
        username = json.get('username', "")
        # Obtain the password from the request
        password = json.get('password', "")
        # Find a user from the password token. If this fail, the user has not been authenticated.
        user:User = allowed_user_query.filter((User._password_hash == password) & (User.username == username)& (User.isactivated == True)).first()
        # Check if the user is authorized
        if not user:
            return make_response({'error': "Unauthorized: you must be logged in to make that request"}, 401)
        # Obtain the match request id from the request
        match_request_id = json.get('match_request_id', "")
        # Find a match_request from id
        match_request:MatchRequest = MatchRequest.query.filter(MatchRequest.id == match_request_id).first()
        # Validate if the match_request exists
        if not match_request:
            return make_response({'error': "Cannot find the match"}, 422)
        # Perform DELETE operation for the match request
        db.session.delete(match_request)
        # Commit database changes
        db.session.commit()
        # Return the public data of the deleted match request
        return make_response(match_request.public_dict(user.id), 200)
# Add RejectMatchRequest method to the routing system. 
api.add_resource(RejectMatchRequest, '/reject_match_request', endpoint='reject_match_request')

# GET request
# Fields
# -- password | Encrypted user password.
# -- username | Accessor's username.
class GetUsers(Resource):
    def get(self):
        # Set the scope of allowed users to call this function
        allowed_user_query = User.query.filter((User.isbanned == False))
        # Get the parameters of this request
        json = request.get_json()
        # Obtain the username from the request
        username = json.get('username', "")
        # Obtain the password from the request
        password = json.get('password', "")
        # Find a user from the password token. If this fail, the user has not been authenticated.
        user:User = allowed_user_query.filter((User._password_hash == password) & (User.username == username)).first()
        # Check if the user is authorized
        if not user:
            return make_response({'error': "Unauthorized: you must be logged in to make that request"}, 401)
        # Find all users from the query (who are activated and not hidden)
        users = User.query.filter((User.isactivated == True) & (User.ishidden == False)).all()
        # Reverse Sort all users by their elo
        users.sort(key=lambda u: u.elo, reverse=True)
        # Convert each class to a dictionary by using public_dict
        for i in range(len(users)):
            users[i] = users[i].public_dict()
        # Return the public data of all users
        return make_response(users, 200)
# Add GetUsers method to the routing system. 
api.add_resource(GetUsers, '/users', endpoint='users')   

class AdminInspect(Resource):
    def get(self):
        # Set the scope of allowed users to call this function
        allowed_user_query = User.query.filter((User.isbanned == False) & (User.isadmin == True))
        # Get the parameters of this request
        json = request.get_json()
        # Obtain the username from the request
        username = json.get('username', "")
        # Obtain the password from the request
        password = json.get('password', "")
        # Find a user from the password token. If this fail, the user has not been authenticated.
        user:User = allowed_user_query.filter((User._password_hash == password) & (User.username == username)).first()
        # Check if the user is authorized
        if not user:
            return make_response({'error': "Unauthorized: you must be logged in to make that request"}, 401)
        # Obtain the id of the user getting inspected
        inspect_id = int(json.get('inspect', ""))
        inspect:User = User.query.get(inspect_id)
        if not inspect:
            return make_response({'error': "Target selected does not exist"}, 401)
        matches = Match.query.filter((Match.user1_id == inspect_id) | (Match.user2_id == inspect_id)).all()
        for i in range(len(matches)):
            matches[i] = matches[i].public_dict(inspect_id)
        match_requests = MatchRequest.query.filter((MatchRequest.user1_id == inspect_id) | (MatchRequest.user2_id == inspect_id)).all()
        for i in range(len(match_requests)):
            match_requests[i] = match_requests[i].public_dict(inspect_id)
        response = {
            "user": inspect.admin_dict(),
            "matches": matches,
            "match_requests": match_requests
        }
        return make_response(response, 200)
# Add AdminInspect method to the routing system. 
api.add_resource(AdminInspect, '/a_inspect', endpoint='a_inspect')      

# * ADMIN
# GET request
# Fields
# -- password | Encrypted user password.
# -- username | Accessor's username.
class AdminGetUsers(Resource):
    def get(self):
        # Set the scope of allowed users to call this function
        allowed_user_query = User.query.filter((User.isbanned == False) & (User.isadmin == True))
        # Get the parameters of this request
        json = request.get_json()
        # Obtain the username from the request
        username = json.get('username', "")
        # Obtain the password from the request
        password = json.get('password', "")
        # Find a user from the password token. If this fail, the user has not been authenticated.
        user:User = allowed_user_query.filter((User._password_hash == password) & (User.username == username)).first()
        # Check if the user is authorized
        if not user:
            return make_response({'error': "Unauthorized: you must be logged in to make that request"}, 401)
        # Find all users from the query (who are activated and not hidden)
        users = User.query.filter().all()
        # Reverse Sort all users by their elo
        users.sort(key=lambda u: u.elo, reverse=True)
        # Convert each class to a dictionary by using public_dict
        for i in range(len(users)):
            users[i] = users[i].admin_dict()
        # Return the public data of all users
        return make_response(users, 200)
# Add AdminGetUsers method to the routing system. 
api.add_resource(AdminGetUsers, '/a_users', endpoint='a_users')

class AdminBan(Resource):
    def post(self):
        # Set the scope of allowed users to call this function
        allowed_user_query = User.query.filter((User.isbanned == False) & (User.isadmin == True))
        # Get the parameters of this request
        json = request.get_json()
        # Obtain the username from the request
        username = json.get('username', "")
        # Obtain target's id from the request
        target_id = json.get('target_id', "")
        # Obtain the password from the request
        password = json.get('password', "")
        # Obtain if the user is banned or unbanned
        ban = json.get('ban', True)
        # Find a user from the password token. If this fail, the user has not been authenticated.
        user:User = allowed_user_query.filter((User._password_hash == password) & (User.username == username)).first()
        # Check if the user is authorized
        if not user:
            return make_response({'error': "Unauthorized: you must be logged in to make that request"}, 401)
        target = User.query.filter(User.isadmin == False).filter((User.id == target_id)).first()
        if not target:
            return make_response({'error': "Ban target is not specified"}, 401)
        # Set the target's ban status
        setattr(target, "isbanned", ban)
        # Commit database changes
        db.session.commit()
        # Return the admin data of the user
        return make_response(target.admin_dict(), 200)
# Add AdminBan method to the routing system. 
api.add_resource(AdminBan, '/a_ban', endpoint='a_ban') 

class AdminHide(Resource):
    def post(self):
        # Set the scope of allowed users to call this function
        allowed_user_query = User.query.filter((User.isbanned == False) & (User.isadmin == True))
        # Get the parameters of this request
        json = request.get_json()
        # Obtain the username from the request
        username = json.get('username', "")
        # Obtain target's id from the request
        target_id = json.get('target_id', "")
        # Obtain the password from the request
        password = json.get('password', "")
        # Obtain if the user is banned or unbanned
        hide = json.get('hide', True)
        # Find a user from the password token. If this fail, the user has not been authenticated.
        user:User = allowed_user_query.filter((User._password_hash == password) & (User.username == username)).first()
        # Check if the user is authorized
        if not user:
            return make_response({'error': "Unauthorized: you must be logged in to make that request"}, 401)
        target = User.query.filter((User.id == target_id)).first()
        if not target:
            return make_response({'error': "Hiding target is not specified"}, 401)
        # Set the target's ban status
        setattr(target, "ishidden", hide)
        # Commit database changes
        db.session.commit()
        # Return the admin data of the user
        return make_response(target.admin_dict(), 200)
# Add AdminHide method to the routing system. 
api.add_resource(AdminHide, '/a_hide', endpoint='a_hide')         

# Run the application if this file is set as main instance
if __name__ == '__main__':
    app.run(port=5555, debug=True)