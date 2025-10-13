from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from utils.auth import login_required

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'change_this_secret_key'
db = SQLAlchemy(app)

# Modèle User
class User(db.Model):
     id = db.Column(db.Integer, primary_key=True)
     username = db.Column(db.String(80), unique=True, nullable=False)
     password = db.Column(db.String(200), nullable=False)

     def set_password(self, password):
          self.password = generate_password_hash(password)

     def check_password(self, password):
          return check_password_hash(self.password, password)
# Crée les tables
with app.app_context():
    db.create_all()

# Route principale
@app.route('/')
@login_required
def index():
    return render_template('index.html')

# Route de connexion
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            flash('Connexion réussie.')
            return redirect(url_for('index'))
        else:
            flash('Nom d’utilisateur ou mot de passe incorrect.')
            return redirect(url_for('login'))
    return render_template('login.html')

# Route d'inscription
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Nom d’utilisateur déjà pris.')
            return redirect(url_for('register'))
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Inscription réussie. Connectez-vous.')
        return redirect(url_for('login'))
    return render_template('register.html')

# Route de déconnexion
@app.route('/logout')
@login_required
def logout():
    session.pop('user_id', None)
    flash('Déconnexion réussie.')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)