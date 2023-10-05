from app import (
    app,
    db,
)
from flask_bcrypt import Bcrypt
from models import User

bcrypt = Bcrypt(app)  # Initializing bcrypt

# Iterate through existing users and update password hashes
with app.app_context():
    for user in User.query.all():
        hashed_password = bcrypt.generate_password_hash(user.password).decode("utf-8")
        user.password = hashed_password

    db.session.commit()

print("Password hashes updated successfully")
