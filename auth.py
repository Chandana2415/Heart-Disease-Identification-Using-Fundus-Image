from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, current_user, login_required
from models import db, User, LoginHistory
from datetime import datetime, timedelta
import secrets

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('user.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password) and user.is_active:
            # Log successful login
            login_history = LoginHistory(
                user_id=user.id,
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string,
                success=True
            )
            db.session.add(login_history)
            
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            user.login_count += 1
            db.session.commit()
            
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('user.dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('user.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('auth.register'))
        
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_active=True
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('user.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate a simple token (in production, use proper email-based tokens)
            reset_token = secrets.token_urlsafe(32)
            
            # Store token in session with expiry (15 minutes)
            session['reset_token'] = reset_token
            session['reset_email'] = email
            session['reset_expiry'] = (datetime.utcnow() + timedelta(minutes=15)).isoformat()
            
            # Redirect directly to reset password page
            flash('Please enter your new password below.', 'info')
            return redirect(url_for('auth.reset_password', token=reset_token))
        else:
            flash('If an account exists with this email, a reset link has been sent.', 'info')
            return redirect(url_for('auth.login'))
    
    return render_template('auth/forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('user.dashboard'))
    
    # Verify token
    stored_token = session.get('reset_token')
    reset_email = session.get('reset_email')
    reset_expiry = session.get('reset_expiry')
    
    if not stored_token or stored_token != token:
        flash('Invalid or expired reset link', 'danger')
        return redirect(url_for('auth.login'))
    
    # Check expiry
    if reset_expiry:
        expiry_time = datetime.fromisoformat(reset_expiry)
        if datetime.utcnow() > expiry_time:
            flash('Reset link has expired. Please request a new one.', 'danger')
            session.pop('reset_token', None)
            session.pop('reset_email', None)
            session.pop('reset_expiry', None)
            return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('auth/reset_password.html', token=token)
        
        if len(new_password) < 6:
            flash('Password must be at least 6 characters long', 'danger')
            return render_template('auth/reset_password.html', token=token)
        
        user = User.query.filter_by(email=reset_email).first()
        if user:
            user.set_password(new_password)
            db.session.commit()
            
            # Clear session
            session.pop('reset_token', None)
            session.pop('reset_email', None)
            session.pop('reset_expiry', None)
            
            flash('Password successfully reset! Please login with your new password.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('User not found', 'danger')
            return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', token=token)