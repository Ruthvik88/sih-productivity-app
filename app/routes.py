from flask import render_template, request, flash, redirect, url_for, session, abort, jsonify
from app import app, db
from app.models import User, Goal, ProgressUpdate # Import the new model
from datetime import datetime

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
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
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

    goals = user.goals.order_by(Goal.status.asc()).all()
    score = user.calculate_performance_score()
    
    reports_data = []
    chart_labels = []
    chart_data = []
    
    if user.role == 'Manager':
        for report in user.reports:
            report_score = report.calculate_performance_score()
            # --- THIS IS THE FIX ---
            # Sort the employee's goals here in the backend before sending to the template
            sorted_employee_goals = report.goals.order_by(Goal.status.asc()).all()
            
            reports_data.append({
                'employee': report, 
                'score': report_score,
                'sorted_goals': sorted_employee_goals # Pass the pre-sorted list to the template
            })
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

# --- OVERHAULED FOR PROOF OF UPDATE ---
@app.route('/update_goal/<int:goal_id>', methods=['POST'])
def update_goal(goal_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401

    goal = Goal.query.get_or_404(goal_id)
    user = User.query.get(session['user_id'])

    if goal.employee.id != user.id:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    # Get data from the new modal form
    progress = request.form.get('progress', type=int)
    status = request.form.get('status')
    comment = request.form.get('comment')
    proof_url = request.form.get('proof_url')

    if not comment:
        return jsonify({'success': False, 'message': 'An update comment is required.'}), 400

    # 1. Create the permanent audit record
    new_update = ProgressUpdate(
        update_value=progress,
        comment=comment,
        proof_url=proof_url,
        author=user,
        goal=goal
    )
    db.session.add(new_update)

    # 2. Update the goal's main values
    goal.current_value = progress
    goal.status = status
    
    db.session.commit()
    
    # 3. Check for league promotion
    user.update_league()
    db.session.commit() # Commit the league change
    
    return jsonify({'success': True, 'message': 'Progress updated successfully!'})


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


@app.route('/create_goal', methods=['GET', 'POST'])
def create_goal():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
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
            
            if user.role == 'Administrator':
                return redirect(url_for('organization'))
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid employee or manager selected.', 'error')

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


# --- NEW ROUTE TO FETCH GOAL HISTORY ---
@app.route('/get_goal_history/<int:goal_id>')
def get_goal_history(goal_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401

    user = User.query.get(session['user_id'])
    goal = Goal.query.get_or_404(goal_id)

    # Check if the user is the employee OR the employee's manager
    is_authorized = False
    if goal.employee.id == user.id:
        is_authorized = True
    if user.role == 'Manager' and goal.employee.manager_id == user.id:
        is_authorized = True

    if not is_authorized:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    updates = []
    # Fetch updates and order them by newest first
    for update in goal.updates.order_by(ProgressUpdate.timestamp.desc()).all():
        updates.append({
            'value': update.update_value,
            'comment': update.comment,
            'proof': update.proof_url,
            'author': update.author.full_name,
            'timestamp': update.timestamp.strftime('%d-%b-%Y %I:%M %p')
        })

    return jsonify({'success': True, 'history': updates, 'goal_title': goal.title})

