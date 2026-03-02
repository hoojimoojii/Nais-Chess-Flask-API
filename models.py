from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import func

from config import db, bcrypt

# Every authenticated client of the server
class User(db.Model):
    # Config the table name
    __tablename__ = 'users'

    # Set the primary key
    id = db.Column(db.Integer, primary_key = True)
    # Set the variables
    name = db.Column(db.String) # Real name of the user
    username = db.Column(db.String) # Fake name of the user (public name)
    isactivated = db.Column(db.Boolean, server_default='t', default=True) # Is the account activated?
    ishidden = db.Column(db.Boolean, server_default='f', default=False) # Is the account hidden?
    isbanned = db.Column(db.Boolean, server_default='f', default=False) # Is the account banned?
    ismanager = db.Column(db.Boolean, server_default='f', default=False) # Is this an admin account?
    isadmin = db.Column(db.Boolean, server_default='f', default=False) # Is this an admin account?
    elo = db.Column(db.Integer, server_default='300', default=300) # User's current elo score
    _password_hash = db.Column(db.String) # Encrypted version of the password

    # Public data of the user
    def public_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "isactivated": self.isactivated,
            "elo": self.elo
        }
    
    # Admin data of the user
    def admin_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "username": self.username,
            "isactivated": self.isactivated,
            "isadmin": self.isadmin,
            "ishidden": self.ishidden,
            "isbanned": self.isbanned,
            "ismanager": self.ismanager,
            "elo": self.elo
        }

    # Private data of the user
    def private_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "username": self.username,
            "password": self._password_hash,
            "isactivated": self.isactivated,
            "isadmin": self.isadmin,
            "ishidden": self.ishidden,
            "isbanned": self.isbanned,
            "ismanager": self.ismanager,
            "elo": self.elo
        }

    @hybrid_property
    def password_hash(self):
        raise Exception('Password hashes may not be viewed.')
    
    # Encrypts the password
    @password_hash.setter
    def password_hash(self, password):
        # Password is encrypted by using bcrypt
        password_hash = bcrypt.generate_password_hash(
            password.encode('utf-8'))
        self._password_hash = password_hash.decode('utf-8')
    
    # Checks if the password is correct
    def authenticate(self, password):
        return bcrypt.check_password_hash(
            self._password_hash, password.encode('utf-8'))
    
    # Record the elo by using the elo formula
    # rB is the opponent's elo
    # sA determines the result of the match (0: Lose, 0.5: Draw, 1: Win)
    def record(self, rB, sA):
        rA = self.elo
        qA = 10 ** (rA / 400)
        qB = 10 ** (rB / 400)
        eA = qA / (qA + qB)
        self.elo = int(self.elo + 40 * (sA-eA))
        if(self.elo < 0):
            self.elo = 0
        db.session.commit()
    
    # Serialize the password everytime
    serialize_rules = ('-_password_hash', )

# Requested chess matches that are pending
class MatchRequest(db.Model):
    # Config the table name
    __tablename__ = 'match_requests'

    # Set the primary key
    id = db.Column(db.Integer, primary_key = True)
    # Set the variables
    user1_id = db.Column(db.Integer) # User who requested the match
    user2_id = db.Column(db.Integer) # User who has to accept or reject the match
    result = db.Column(db.String) # Result of the match
    request_time = db.Column(db.DateTime, server_default=func.now()) # Time when the time is requested

    # Public data of the user. Accessor is the id of the user who's accessing the data.
    def public_dict(self, accessor):
        accessor = int(accessor)
        user1:User = User.query.filter(User.id == self.user1_id).first()
        user2:User = User.query.filter(User.id == self.user2_id).first()
        if(accessor == self.user2_id):
            return {
                "id": self.id,
                "user1": user1.public_dict(),
                "user2": user2.public_dict(),
                "result": self.reverse_result(),
                "request_time": self.request_time
            }
        else:
            return {
                "id": self.id,
                "user1": user1.public_dict(),
                "user2": user2.public_dict(),
                "result": self.result,
                "request_time": self.request_time
            }
    
    # Reverse the result.
    def reverse_result(self):
        if(self.result == "Win"):
            return "Lose"
        elif(self.result == "Lose"):
            return "Win"
        return "Draw"
    
# Chess matches that have been accepted by both sides
class Match(db.Model):
    # Config the table name
    __tablename__ = 'matches'
    
    # Set the primary key
    id = db.Column(db.Integer, primary_key = True)
    # Set the variables
    user1_id = db.Column(db.Integer) # User who requested the match
    user2_id = db.Column(db.Integer) # User who accepted the match
    result = db.Column(db.String) # Result of the match
    time = db.Column(db.DateTime) # Time when the match was requested
    
    # Public data of the user. Accessor is the id of the user who's accessing the data.
    def public_dict(self, accessor):
        accessor = int(accessor)
        user1:User = User.query.get(self.user1_id)
        user2:User = User.query.get(self.user2_id)
        if(accessor == self.user2_id):
            return {
                "id": self.id,
                "user1": user1.public_dict(),
                "user2": user2.public_dict(),
                "result": self.reverse_result(),
                "time": self.time
            }
        else:
            return {
                "id": self.id,
                "user1": user1.public_dict(),
                "user2": user2.public_dict(),
                "result": self.result,
                "time": self.time
            }
    
    # Reverse the result.
    def reverse_result(self):
        if(self.result == "Win"):
            return "Lose"
        elif(self.result == "Lose"):
            return "Win"
        return "Draw"
    
    # Get the integer value of result.
    def sA(self):
        if(self.result == "Win"):
            return 1
        elif(self.result == "Lose"):
            return 0
        else:
            return 0.5
        
    def sB(self):
        return 1-self.sA()
    
    # Modify the elo for both users according to the result.
    def record(self):
        # Fetch both users from the database using id
        user1:User = User.query.filter(User.id == self.user1_id).first()
        user2:User = User.query.filter(User.id == self.user2_id).first()
        # In case anyone anyone is not there
        if((not user1) or (not user2)):
            return False;
        # Save the first user's elo before modifying it
        temp = user1.elo
        # Modify the elo of first user
        user1.record(user2.elo, self.sA())
        # Modify the elo of second user
        user2.record(temp, self.sB())
        # No errors!
        return True;