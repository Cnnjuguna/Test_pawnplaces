from dotenv import load_dotenv

load_dotenv()

from flask import Flask, jsonify, make_response, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_restful import Api, Resource, reqparse
from models import db, DogHouse, User, Review
from flask_cors import CORS
from flask_marshmallow import Marshmallow
from werkzeug.security import check_password_hash

# --------------------------------------------------------#
from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    SubmitField,
    BooleanField,
    TextAreaField,
    SelectField,
    IntegerField,
)
from wtforms.validators import (
    InputRequired,
    Length,
    Email,
    EqualTo,
    ValidationError,
    NumberRange,
)
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity,
)

# ---------------------------------------------------------#
import logging
import cloudinary
from cloudinary.uploader import upload
from cloudinary.utils import cloudinary_url
import cloudinary.api
import os
from flask_bcrypt import Bcrypt


app = Flask(__name__)
api = Api(app)
bcrypt = Bcrypt(app)

logger = logging.getLogger(__name__)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


# Generating a random 32-character hexadecimal string as the secret key
secret_key = os.urandom(32).hex()


# app.config["SECRET_KEY"] = "your_secret_key_here"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True
app.config["JWT_SECRET_KEY"] = secret_key

cors = CORS(app)
ma = Marshmallow(app)
jwt = JWTManager(app)
migrate = Migrate(app, db)
db.init_app(app)


# # Cloudinary configuration
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
)


# ----------------------------------------Forms for Input Validation---------------------------------------------------#
# Forms for Input Validation
class UserRegistrationForm(FlaskForm):
    username = StringField(
        "Username", validators=[InputRequired(), Length(min=4, max=30)]
    )
    email = StringField("Email", validators=[InputRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[InputRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "ConfirmPassword", validators=[InputRequired(), EqualTo("password")]
    )
    submit = SubmitField("Sign Up")

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError("Username already exists")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError("Email already exists")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[InputRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[InputRequired(), Length(6)])
    remember = BooleanField("Remember Me")
    submit = SubmitField("Login")


class CreateNewReviewForm(FlaskForm):
    title = StringField("Title", validators=[InputRequired(), Length(min=1, max=100)])
    body = TextAreaField("Body", validators=[InputRequired(), Length(min=1, max=500)])
    user_id = IntegerField("User ID", validators=[InputRequired(), NumberRange(min=1)])
    doghouse_id = IntegerField(
        "Dog House ID", validators=[InputRequired(), NumberRange(min=1)]
    )
    # is_booked = SelectField("is_booked", choices=[("Booked", "Booked"), ("Available", "Available"), ("Draft", "Draft")])
    submit = SubmitField("Create Review")


class UserSchema(ma.Schema):
    class Meta:
        model = User
        load_instance = True

        fields = ("id", "username", "email", "password")


user_schema = UserSchema()
users_schema = UserSchema(many=True)


class DogHouseSchema(ma.Schema):
    class Meta:
        model = DogHouse

        load_instance = True
        # Fields to expose
        fields = (
            "id",
            "name",
            "location",
            "description",
            "price_per_night",
            "image_url",
            "amenities",
            "is_booked",
        )


doghouse_schema = DogHouseSchema()
doghouses_schema = DogHouseSchema(many=True)


class ReviewSchema(ma.Schema):
    class Meta:
        load_instance = True
        # Fields to expose
        fields = ("id", "title", "body", "user_id", "doghouse_id", "status")


review_schema = ReviewSchema()
reviews_schema = ReviewSchema(many=True)


# RESTFUL API Endpoints
api = Api(app)


class Index(Resource):
    def get(self):
        response_dict = {
            "index": "Welcome to the Paws and Places RESTful API",
        }

        response = make_response(jsonify(response_dict), 200)

        return response


# Route Home
@app.route("/")
def home():
    response_dict = {
        "index": "Welcome to Paws and Places RESTful API.",
    }
    response = make_response(jsonify(response_dict), 200)

    return response


# -----------------------------Routes for Login and Logout------------------------------#
from flask_bcrypt import check_password_hash


@app.route("/jwt-login", methods=["POST"])
def jwt_login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()

    if user:
        stored_password_hash = (
            user.password
        )  # Retrieving the hashed password from the database

        # Comparing the hashed login password with the stored password hash
        if check_password_hash(stored_password_hash, password):
            # Successful login, generate an access token
            access_token = create_access_token(identity=user.id)
            return jsonify({"access_token": access_token}), 200
        else:
            # Invalid password
            return jsonify({"message": "Invalid login credentials"}), 401
    else:
        # User with provided email not found
        return jsonify({"message": "Invalid login credentials"}), 401


# Protected route
@app.route("/protected", methods=["GET"])
@jwt_required()
def protected_route():
    current_user = get_jwt_identity()
    return jsonify(message=f"Hello, {current_user}! This is a protected route."), 200


# Users will be redirected to the login page if they haven't logged in
@app.route("/profile")
@login_required
def profile():
    return jsonify({"user_id": current_user.id, "username": current_user.username}), 200


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logout successful"}), 200


# ----------------------------Routes for SignUp----------------------------------#

from flask import render_template, redirect, url_for, flash


@app.route("/signup", methods=["POST"])
def signup():
    data = request.json
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    # Hash the password using bcrypt
    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

    # Create a new user with the hashed password
    new_user = User(username=username, email=email, password=hashed_password)

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201


# User ROUTES
# -----------------------------------------------------------------------------------------#
# Route GET users
@app.route("/users", methods=["GET"])
def get_user():
    users = [user.to_dict() for user in User.query.all()]
    result = users_schema.dump(users)
    return jsonify(result), 200


# Route to GET, PATCH, DELETE a user by ID
@app.route("/users/<int:user_id>", methods=["GET", "PATCH", "DELETE"])
def get_user_by_id(user_id):
    user = User.query.filter_by(id=user_id).first()
    if user is None:  # Does not exist
        return jsonify({"message": "User not found"}), 404
    else:
        if request.method == "GET":
            result = user_schema.dump(user)
            response = make_response(jsonify(result), 200)
            return response

        elif request.method == "PATCH":
            data = request.json()
            errors = user_schema.dump(data)
            if errors:
                return jsonify(errors), 400

            for key, value in data.items():
                setattr(user, key, value)
            db.session.commit()

            result = user_schema.dump(user)
            return jsonify(result), 200

        elif request.method == "DELETE":
            db.session.delete(user)
            db.session.commit()

            return jsonify({"message": "User deleted"}), 204


# Route to POST create a user
@app.route("/users", methods=["POST"])
def create_user():
    data = request.json
    errors = user_schema.validate(data)

    if errors:
        return jsonify(errors), 400

    # Hash the password using bcrypt
    hashed_password = bcrypt.generate_password_hash(data["password"]).decode("utf-8")

    # Create a new user with the hashed password
    new_user = User(
        username=data["username"], email=data["email"], password=hashed_password
    )

    db.session.add(new_user)
    db.session.commit()

    result = user_schema.dump(new_user)
    return jsonify(result), 201


# Doghouse ROUTES
# -----------------------------------------------------------------------------------------#
@app.route("/doghouses", methods=["GET"])
def get_doghouses():
    doghouses = [house.to_dict() for house in DogHouse.query.all()]

    result = doghouses_schema.dump(doghouses)
    return jsonify(result), 200


# Route to GET, PATCH, DELETE a DogHouse
@app.route("/doghouses/<int:doghouse_id>", methods=["GET", "PATCH", "DELETE"])
def get_doghouse_by_id(doghouse_id):
    doghouse = DogHouse.query.filter_by(id=doghouse_id).first()
    if doghouse is None:
        return jsonify({"message": "Dog house not found"}), 404

    # GET
    if request.method == "GET":
        result = doghouse_schema.dump(doghouse)
        return jsonify(result), 200

    # PATCH
    elif request.method == "PATCH":
        data = request.json
        errors = doghouse_schema.validate(data)
        if errors:
            return jsonify(errors), 400
        for key, value in data.items():
            setattr(doghouse, key, value)
        db.session.commit()
        result = doghouse_schema.dump(doghouse)
        return jsonify(result), 200

    # DELETE
    elif request.method == "DELETE":
        db.session.delete(doghouse)
        db.session.commit()
        return jsonify({"message": "Dog house deleted"}), 204


# Route to POST a doghouse
@app.route("/doghouses", methods=["POST"])
def create_dog_house_listing():
    data = request.json

    # Validate the "is_booked" attribute
    if "is_booked" in data and data["is_booked"] not in ["Booked", "Available"]:
        return (
            jsonify(
                {
                    "message": "Invalid value for 'is_booked'. It must be 'Booked' or 'Available'"
                }
            ),
            400,
        )

    # Create a new DogHouse object and save it to the database
    new_doghouse = DogHouse(**data)

    db.session.add(new_doghouse)
    db.session.commit()

    result = doghouse_schema.dump(new_doghouse)
    return jsonify(result), 201


# Reviews ROUTES
# -----------------------------------------------------------------------------------------#


# Route to retrieve all reviews
@app.route("/reviews/", methods=["GET"])
@app.route("/reviews", methods=["GET"])
def get_reviews():
    reviews = [review.to_dict() for review in Review.query.all()]
    result = reviews_schema.dump(reviews)
    return jsonify(result), 200


# Route to create a new review
@app.route("/reviews", methods=["POST"])
def create_review():
    data = request.json
    errors = review_schema.validate(data)
    if errors:
        return jsonify(errors), 400

    new_review = Review(**data)
    db.session.add(new_review)
    db.session.commit()

    result = review_schema.dump(new_review)
    return jsonify(result), 201


# Route to retrieve a review by ID
@app.route("/reviews/<int:review_id>", methods=["GET"])
def get_review_by_id(review_id):
    review = Review.query.filter_by(id=review_id).first()
    if review is None:
        return jsonify({"message": "Review not found"}), 404

    result = review_schema.dump(review)
    return jsonify(result), 200


# Route to update a review by ID
@app.route("/reviews/<int:review_id>", methods=["PUT"])
def update_review_by_id(review_id):
    data = request.json
    review = Review.query.filter_by(id=review_id).first()
    if review is None:
        return jsonify({"message": "Review not found"}), 404

    for key, value in data.items():
        setattr(review, key, value)
    db.session.commit()

    result = review_schema.dump(review)
    return jsonify(result), 200


# Route to delete a review by ID
@app.route("/reviews/<int:review_id>", methods=["DELETE"])
def delete_review_by_id(review_id):
    review = Review.query.filter_by(id=review_id).first()
    if review is None:
        return jsonify({"message": "Review not found"}), 404

    db.session.delete(review)
    db.session.commit()

    return jsonify({"message": "Review deleted"}), 204


@app.route("/doghouses/<int:doghouse_id>/reviews", methods=["GET"])
def get_doghouse_reviews(doghouse_id):
    # code to query the db and get the doghouse reviews
    reviews = Review.query.filter_by(doghouse_id=doghouse_id).all()

    reviews_data = [review.to_dict() for review in reviews]

    return jsonify(reviews_data)


if __name__ == "__main__":
    app.run(debug=True, port=5555)
