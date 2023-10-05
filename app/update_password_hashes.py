from app import (
    app,
    db,
)  # Replace 'your_flask_app' with the actual name of your Flask app
from flask_bcrypt import Bcrypt
from models import User  # Import your User model

bcrypt = Bcrypt(app)  # Initialize bcrypt

# Iterate through existing users and update password hashes
with app.app_context():
    for user in User.query.all():
        hashed_password = bcrypt.generate_password_hash(user.password).decode("utf-8")
        user.password = hashed_password

    db.session.commit()

print("Password hashes updated successfully")
