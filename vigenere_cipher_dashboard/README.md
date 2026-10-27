# CRYPTLAB — Vigenère Cipher Dashboard

A responsive Flask application for demonstrating the Vigenère cipher, including encryption/decryption, repeated-key visualization, per-character calculations, the 26×26 tabula recta, SQLite history, and activity statistics.

## Features
- Session-based login with hashed passwords
- Vigenère encryption and decryption
- Preserves spaces, punctuation, digits, and original letter case; non-ASCII letters are left unchanged
- Key repeats only over ASCII alphabetic message characters
- Step-by-step numeric calculations and tabula recta visualization
- Copy and download result
- SQLite operation history with inspect and delete actions
- Statistics backed by the database
- Responsive dark cybersecurity UI

## Technology
Python, Flask, Flask-SQLAlchemy, SQLite, HTML, CSS, Bootstrap 5, JavaScript, Font Awesome.

## Run locally
Python 3.10+ recommended.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000.

## Demo login
- Username: `admin`
- Password: `admin123`

The first run creates this account with a hashed password. For deployment, set a strong `ADMIN_PASSWORD` before the first database initialization, set a random `SECRET_KEY`, and use persistent storage for SQLite. If the database already exists, changing `ADMIN_PASSWORD` will not automatically reset the existing account password.

Example environment variables:

```text
SECRET_KEY=a-long-random-secret
ADMIN_PASSWORD=use-a-unique-strong-password
FLASK_DEBUG=0
```

## Deploying link
https://vigenere-cipher-dashboard.onrender.com/dashboard

## Algorithm
Letters are mapped A=0 through Z=25.

- Encryption: `C = (P + K) mod 26`
- Decryption: `P = (C - K + 26) mod 26`

This project is for education only. Vigenère is not suitable for protecting real-world secrets.
