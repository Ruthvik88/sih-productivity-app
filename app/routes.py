from flask import render_template, request, flash, redirect, url_for, session, abort, jsonify
from app import app, db
from app.models import User, Goal

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user.role == 'Administrator':
            return redirect(url_for('organization'))
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        # --- THIS IS THE FIX ---
        # We must find the user by the email from the form, not from the session.
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            
            # This line makes the session cookie expire when the browser is closed.
            session.permanent = False
            
            flash('Login successful!')
            
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
    if user.role == 'Administrator':
        return redirect(url_for('organization'))

    goals = user.goals.all()
    score = user.calculate_performance_score()
    
    reports_data = []
    chart_labels = []
    chart_data = []
    
    if user.role == 'Manager':
        for report in user.reports:
            report_score = report.calculate_performance_score()
            reports_data.append({'employee': report, 'score': report_score})
            chart_labels.append(report.full_name)
            chart_data.append(report_score)

    return render_template(
        'dashboard.html', 
        user=user, 
        goals=goals, 
        score=score, 
        reports_data=reports_data,
        chart_labels=chart_labels,
        chart_data=chart_data
    )

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
            total_progress = sum(goal.get_progress() * goal.weight for goal in team_goals)
            total_weight = sum(goal.weight for goal in team_goals)
            average_progress = int(total_progress / total_weight) if total_weight > 0 else 0
        else:
            average_progress = 0
            
        managers_data.append({'info': manager, 'avg_progress': average_progress})
    
    return render_template('organization.html', title='Organizational View', user=user, managers_data=managers_data)


# --- MODIFIED FOR NEW FEATURE ---
@app.route('/create_goal', methods=['GET', 'POST'])
def create_goal():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    # Allow both Managers and Administrators to access this page
    if user.role not in ['Manager', 'Administrator']:
        abort(403)

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        assignee_id = request.form.get('assignee')
        kpi_name = request.form.get('kpi_name')
        target_value = request.form.get('target_value', type=int)
        weight = request.form.get('weight', type=int)

        assignee = User.query.get(assignee_id)
        
        # Validation: Check if the current user is authorized to assign a goal to the selected user
        is_authorized = False
        if user.role == 'Manager' and assignee and assignee.manager_id == user.id:
            is_authorized = True
        if user.role == 'Administrator' and assignee and assignee.role == 'Manager':
            is_authorized = True

        if is_authorized:
            new_goal = Goal(
                title=title, 
                description=description, 
                kpi_name=kpi_name,
                target_value=target_value,
                weight=weight,
                employee=assignee
            )
            db.session.add(new_goal)
            db.session.commit()
            flash('New goal has been assigned successfully!')
            # Redirect admins to organization view, managers to dashboard
            if user.role == 'Administrator':
                return redirect(url_for('organization'))
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid employee or manager selected.', 'error')

    # Determine who to show in the assignee dropdown
    assignees = []
    if user.role == 'Manager':
        assignees = user.reports.all()
    elif user.role == 'Administrator':
        assignees = User.query.filter_by(role='Manager').all()
        
    return render_template('create_goal.html', title='Create New Goal', assignees=assignees, user=user)


@app.route('/add_feedback/<int:goal_id>', methods=['POST'])
def add_feedback(goal_id):
    if 'user_id' not in session:
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
    
    return jsonify({'success': True, 'message': 'Feedback submitted successfully!'})


@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    score = user.calculate_performance_score()
    
    return render_template('profile.html', title='My Profile', user=user, score=score)


@app.route('/get_employee_goals/<int:employee_id>')
def get_employee_goals(employee_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401
    
    manager = User.query.get(session['user_id'])
    if manager.role != 'Manager':
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    employee = User.query.get_or_404(employee_id)
    if employee.manager_id != manager.id:
        return jsonify({'success': False, 'message': 'Not a direct report'}), 403
        
    goals = [{
        'id': goal.id,
        'title': goal.title,
        'progress': goal.get_progress(),
        'feedback': goal.manager_feedback or ''
    } for goal in employee.goals]
    
    return jsonify({'success': True, 'goals': goals, 'employee_name': employee.full_name})

