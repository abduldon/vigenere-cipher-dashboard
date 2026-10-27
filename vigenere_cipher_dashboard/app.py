import os
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from io import BytesIO

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-this-secret-key-before-deployment')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(BASE_DIR, 'database.db'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class Operation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    operation_type = db.Column(db.String(20), nullable=False)
    input_text = db.Column(db.Text, nullable=False)
    key = db.Column(db.String(500), nullable=False)
    result = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User', backref=db.backref('operations', lazy=True, cascade='all, delete-orphan'))


def valid_key(key):
    return any(ch.isalpha() and ch.isascii() for ch in key)

def vigenere(text, key, decrypt=False):
    key_values = [ord(c.upper()) - 65 for c in key if c.isascii() and c.isalpha()]
    if not key_values:
        raise ValueError('Key must contain at least one alphabetic character.')
    out, steps, repeated = [], [], []
    ki = 0
    for pos, ch in enumerate(text, 1):
        if ch.isascii() and ch.isalpha():
            p = ord(ch.upper()) - 65
            k = key_values[ki % len(key_values)]
            value = (p - k + 26) % 26 if decrypt else (p + k) % 26
            result_char = chr(value + 65)
            repeated.append(chr(k + 65))
            formula = f'({p} - {k} + 26) % 26 = {value}' if decrypt else f'({p} + {k}) % 26 = {value}'
            steps.append({'position': len(steps)+1, 'text': ch.upper(), 'key': chr(k+65), 'text_value': p, 'key_value': k, 'formula': formula, 'result': result_char})
            out.append(result_char if ch.isupper() else result_char.lower())
            ki += 1
        else:
            out.append(ch)
            repeated.append(' ' if ch.isspace() else '·')
    return ''.join(out), ''.join(repeated), steps

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.path))
        return fn(*args, **kwargs)
    return wrapper

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session.clear()
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(request.args.get('next') or url_for('dashboard'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', username=session.get('username'))

@app.route('/api/operate', methods=['POST'])
@login_required
def operate():
    data = request.get_json(silent=True) or request.form
    text = (data.get('message') or '').strip('\n')
    key = (data.get('key') or '').strip()
    mode = (data.get('mode') or 'encrypt').lower()
    if not text.strip():
        return jsonify(error='Please enter a message.'), 400
    if not key:
        return jsonify(error='Please enter a key.'), 400
    if not valid_key(key):
        return jsonify(error='Key must contain at least one alphabetic character.'), 400
    if mode not in ('encrypt', 'decrypt'):
        return jsonify(error='Choose encryption or decryption.'), 400
    result, repeated_key, steps = vigenere(text, key, mode == 'decrypt')
    op = Operation(user_id=session['user_id'], operation_type=mode.title(), input_text=text, key=key, result=result)
    db.session.add(op)
    db.session.commit()
    return jsonify(result=result, repeated_key=repeated_key, steps=steps, operation_id=op.id, stats=stats_for(session['user_id']))

def stats_for(user_id):
    ops = Operation.query.filter_by(user_id=user_id).all()
    encrypted = sum(o.operation_type == 'Encrypt' for o in ops)
    decrypted = sum(o.operation_type == 'Decrypt' for o in ops)
    return {'total': len(ops), 'encrypted': encrypted, 'decrypted': decrypted,
            'avg_key_length': round(sum(len(o.key) for o in ops) / len(ops), 1) if ops else 0}

@app.route('/api/statistics')
@login_required
def api_statistics():
    return jsonify(stats_for(session['user_id']))

@app.route('/history')
@login_required
def history():
    ops = Operation.query.filter_by(user_id=session['user_id']).order_by(Operation.created_at.desc()).all()
    return render_template('history.html', operations=ops)

@app.route('/history/<int:operation_id>')
@login_required
def view_operation(operation_id):
    op = Operation.query.filter_by(id=operation_id, user_id=session['user_id']).first_or_404()
    return jsonify(id=op.id, operation_type=op.operation_type, input_text=op.input_text, key=op.key, result=op.result, created_at=op.created_at.strftime('%Y-%m-%d %H:%M UTC'))

@app.route('/history/delete/<int:operation_id>', methods=['POST'])
@login_required
def delete_operation(operation_id):
    op = Operation.query.filter_by(id=operation_id, user_id=session['user_id']).first_or_404()
    db.session.delete(op)
    db.session.commit()
    flash('Operation deleted.', 'success')
    return redirect(url_for('history'))

@app.route('/how-it-works')
@login_required
def how_it_works():
    return render_template('how_it_works.html')

@app.route('/download', methods=['POST'])
@login_required
def download_result():
    result = request.form.get('result', '')
    payload = BytesIO(result.encode('utf-8'))
    payload.seek(0)
    return send_file(payload, as_attachment=True, download_name='vigenere_result.txt', mimetype='text/plain')

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        db.session.add(User(username='admin', password_hash=generate_password_hash(os.environ.get('ADMIN_PASSWORD', 'admin123'))))
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1', host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
