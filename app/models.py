from datetime import datetime
from app import db
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(64), index=True, default='Employee')

    # Link to manager
    manager_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    # Relationships
    goals = db.relationship('Goal', backref='employee', lazy='dynamic')
    reports = db.relationship('User', backref=db.backref('manager', remote_side=[id]), lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.full_name}>'

    # START: New method for calculating score
    def calculate_performance_score(self):
        my_goals = self.goals.all()

        if not my_goals:
            return 0

        # 1. Calculate completion score (70% weight)
        total_progress = sum(goal.current_value for goal in my_goals)
        average_completion = total_progress / len(my_goals)
        completion_score = (average_completion / 100) * 70

        # 2. Calculate status score (30% weight)
        completed_goals = sum(1 for goal in my_goals if goal.status == 'Completed')
        status_ratio = completed_goals / len(my_goals)
        status_score = status_ratio * 30

        # Final score
        final_score = int(completion_score + status_score)
        
        return final_score
    # END: New method

class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    description = db.Column(db.Text)
    kpi_name = db.Column(db.String(100)) # Simplified for MVP
    current_value = db.Column(db.Integer, default=0)
    target_value = db.Column(db.Integer, default=100)
    status = db.Column(db.String(64), index=True, default='In Progress')
    due_date = db.Column(db.DateTime)
    manager_feedback = db.Column(db.Text) # Simplified for MVP

    # This is the foreign key linking a Goal to a User
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return f'<Goal {self.title}>'

