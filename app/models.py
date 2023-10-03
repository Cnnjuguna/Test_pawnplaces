from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey
from sqlalchemy_serializer import SerializerMixin

db = SQLAlchemy()


# Reviews Model
class Review(db.Model, SerializerMixin):
    __tablename__ = "reviews"

    id = db.Column(db.Integer(), primary_key=True)
    title = db.Column(db.String(100))
    body = db.Column(db.String(500))
    rating = db.Column(db.Integer())
    user_id = db.Column(db.Integer(), ForeignKey("users.id"))
    doghouse_id = db.Column(db.Integer(), ForeignKey(column="doghouses.id"))
    status = db.Column(db.String(150))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "rating": self.rating,
            "user_id": self.user_id,
            "doghouse_id": self.doghouse_id,
            "status": self.status,
        }

    def __repr__(self):
        return f"Review: {self.id} | {self.title}"


# User Model
class User(db.Model, SerializerMixin):
    __tablename__ = "users"

    serialize_rules = "-reviews.user"
    id = db.Column(db.Integer(), primary_key=True)
    username = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    # one-to-many Relationship between Users and Reviews
    reviews = db.relationship("Review", backref="user")

    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.password = password

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "password": self.password,
        }

    def __repr__(self):
        return f" User: {self.id} | {self.username}"


# User DogHouse
class DogHouse(db.Model, SerializerMixin):
    __tablename__ = "doghouses"

    serialize_rules = "-reviews.doghouse"
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(200))
    location = db.Column(db.String())
    description = db.Column(db.String(500))
    price_per_night = db.Column(db.Float())
    image_url = db.Column(db.String())
    amenities = db.Column(db.String())
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    # one-to-many Relationship between DogHouse and Reviews
    reviews = db.relationship("Review", backref="doghouse")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "location": self.location,
            "description": self.description,
            "price_per_night": self.price_per_night,
            "image_url": self.image_url,
            "amenities": self.amenities,
        }

    def __repr__(self):
        return f" DogHouse: {self.id} | {self.name} | {self.location} "
