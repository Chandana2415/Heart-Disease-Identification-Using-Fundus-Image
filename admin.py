from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, User, Analysis, LoginHistory
from datetime import datetime, timedelta
from utils.decorators import admin_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    total_analyses = Analysis.query.count()
    
    today_analyses = Analysis.query.filter(
        Analysis.analysis_date >= datetime.utcnow().date()
    ).count()
    
    recent_logins = LoginHistory.query.order_by(
        LoginHistory.login_time.desc()
    ).limit(10).all()
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         active_users=active_users,
                         total_analyses=total_analyses,
                         today_analyses=today_analyses,
                         recent_logins=recent_logins)

@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/user/<int:user_id>')
@login_required
@admin_required
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    analyses = Analysis.query.filter_by(user_id=user_id).order_by(
        Analysis.analysis_date.desc()
    ).all()
    
    login_history = LoginHistory.query.filter_by(user_id=user_id).order_by(
        LoginHistory.login_time.desc()
    ).limit(20).all()
    
    return render_template('admin/user_detail.html',
                         user=user,
                         analyses=analyses,
                         login_history=login_history)

@admin_bp.route('/user/<int:user_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    return jsonify({'success': True, 'is_active': user.is_active})

@admin_bp.route('/user/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Delete user's analyses first
    Analysis.query.filter_by(user_id=user_id).delete()
    
    # Delete user's login history
    LoginHistory.query.filter_by(user_id=user_id).delete()
    
    # Delete the user
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({'success': True})

@admin_bp.route('/analytics')
@login_required
@admin_required
def analytics():
    # User growth data (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    # User registration analytics
    user_registrations = db.session.query(
        db.func.date(User.created_at).label('date'),
        db.func.count(User.id).label('count')
    ).filter(User.created_at >= thirty_days_ago)\
     .group_by(db.func.date(User.created_at))\
     .order_by(db.func.date(User.created_at)).all()
    
    # Analysis activity analytics
    analysis_activity = db.session.query(
        db.func.date(Analysis.analysis_date).label('date'),
        db.func.count(Analysis.id).label('count')
    ).filter(Analysis.analysis_date >= thirty_days_ago)\
     .group_by(db.func.date(Analysis.analysis_date))\
     .order_by(db.func.date(Analysis.analysis_date)).all()
    
    # Login activity analytics
    login_activity = db.session.query(
        db.func.date(LoginHistory.login_time).label('date'),
        db.func.count(LoginHistory.id).label('count')
    ).filter(LoginHistory.login_time >= thirty_days_ago)\
     .group_by(db.func.date(LoginHistory.login_time))\
     .order_by(db.func.date(LoginHistory.login_time)).all()
    
    # Top users by analysis count
    top_users = db.session.query(
        User.id,
        User.email,
        User.first_name,
        User.last_name,
        db.func.count(Analysis.id).label('analysis_count')
    ).join(Analysis, User.id == Analysis.user_id)\
     .group_by(User.id)\
     .order_by(db.func.count(Analysis.id).desc())\
     .limit(10).all()
    
    return render_template('admin/analytics.html',
                         user_registrations=user_registrations,
                         analysis_activity=analysis_activity,
                         login_activity=login_activity,
                         top_users=top_users,
                         thirty_days_ago=thirty_days_ago)