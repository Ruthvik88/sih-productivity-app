from app import app, db
from flask import render_template, request, flash, redirect, url_for, session, abort
from app.models import User, Goal
from app import app, db
from flask import render_template, request, flash, redirect, url_for, session, abort, jsonify
from app.models import User, Goal

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        # Check role for already logged-in users and redirect appropriately
        user = User.query.get(session['user_id'])
        if user.role == 'Administrator':
            return redirect(url_for('organization'))
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            flash('Login successful!')
            
            # New: Redirect based on user role
            if user.role == 'Administrator':
                return redirect(url_for('organization'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.')

    return render_template('login.html', title='Sign In')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    # Prevent Admins from accessing the regular dashboard directly
    if user.role == 'Administrator':
        return redirect(url_for('organization'))

    goals = user.goals.all()
    
    # Calculate score for the logged-in user
    score = user.calculate_performance_score()
    
    reports_data = []
    chart_labels = []
    chart_data = []
    if user.role == 'Manager':
        # Calculate score and prepare chart data for each report
        for report in user.reports:
            report_score = report.calculate_performance_score()
            reports_data.append({'employee': report, 'score': report_score})
            chart_labels.append(report.full_name)
            chart_data.append(report_score)

    return render_template('dashboard.html', user=user, goals=goals, score=score, 
                           reports_data=reports_data, chart_labels=chart_labels, chart_data=chart_data)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.')
    return redirect(url_for('login'))

@app.route('/update_goal/<int:goal_id>', methods=['POST'])
def update_goal(goal_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    goal = Goal.query.get_or_404(goal_id)

    if goal.employee.id != session['user_id']:
        abort(403)

    goal.current_value = int(request.form.get('progress'))
    goal.status = request.form.get('status')
    
    db.session.commit()
    
    flash('Goal updated successfully!')
    return redirect(url_for('dashboard'))

@app.route('/organization')
def organization():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if user.role != 'Administrator':
        abort(403)

    managers = User.query.filter_by(role='Manager').all()
    
    managers_data = []
    for manager in managers:
        team_goals = []
        for employee in manager.reports:
            team_goals.extend(employee.goals.all())
        
        if team_goals:
            total_progress = sum(goal.current_value for goal in team_goals)
            average_progress = int(total_progress / len(team_goals))
        else:
            average_progress = 0
            
        managers_data.append({'info': manager, 'avg_progress': average_progress})
    
    return render_template('organization.html', title='Organizational View', managers_data=managers_data)


@app.route('/create_goal', methods=['GET', 'POST'])
def create_goal():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if user.role != 'Manager':
        abort(403)

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        assignee_id = request.form.get('assignee')

        assignee = User.query.get(assignee_id)
        if assignee and assignee.manager_id == user.id:
            new_goal = Goal(title=title, description=description, employee=assignee)
            db.session.add(new_goal)
            db.session.commit()
            flash('New goal has been assigned successfully!')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid employee selected.', 'error')

    reports = user.reports.all()
    # THIS IS THE FIX: We now pass the 'user' object to the template
    return render_template('create_goal.html', title='Create New Goal', reports=reports, user=user)



@app.route('/add_feedback/<int:goal_id>', methods=['POST'])
def add_feedback(goal_id):
    if 'user_id' not in session:
        # For background requests, return an error status
        return jsonify({'success': False, 'message': 'Authentication required'}), 401
    
    user = User.query.get(session['user_id'])
    if user.role != 'Manager':
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    goal = Goal.query.get_or_404(goal_id)
    if goal.employee.manager_id != user.id:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    feedback_text = request.form.get('feedback')
    goal.manager_feedback = feedback_text
    db.session.commit()
    
    # Instead of redirecting, return a success message as JSON
    return jsonify({'success': True, 'message': 'Feedback submitted successfully!'})



@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    score = user.calculate_performance_score()
    
    return render_template('profile.html', title='My Profile', user=user, score=score)

