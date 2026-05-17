from werkzeug.security import generate_password_hash

password = generate_password_hash("Admin123#")

print(password)