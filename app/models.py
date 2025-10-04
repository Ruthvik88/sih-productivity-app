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

    # --- THIS METHOD IS NOW UPDATED ---
    def calculate_performance_score(self):
        """Calculates a weighted performance score for the user based on their goals."""
        my_goals = self.goals.all()

        if not my_goals:
            return 0
        
        total_weight = sum(goal.weight for goal in my_goals)
        if total_weight == 0:
            return 0 # Avoid division by zero if all goals have a weight of 0

        # Calculate the weighted score based on each goal's progress and weight
        weighted_score = sum(goal.get_progress() * goal.weight for goal in my_goals)
        
        # Normalize the score to a 0-100 scale
        normalized_score = (weighted_score / total_weight)
        
        return int(normalized_score)

class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    description = db.Column(db.Text)
    kpi_name = db.Column(db.String(100))
    current_value = db.Column(db.Integer, default=0)
    target_value = db.Column(db.Integer, default=100)
    # --- THIS COLUMN IS NOW CORRECTED ---
    # It has nullable=False and a default value, which is better for the database
    weight = db.Column(db.Integer, default=5, nullable=False)
    status = db.Column(db.String(64), index=True, default='In Progress')
    due_date = db.Column(db.DateTime)
    manager_feedback = db.Column(db.Text)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return f'<Goal {self.title}>'

    # --- THIS IS THE NEW, REQUIRED METHOD ---
    def get_progress(self):
        """Calculates the percentage progress of a goal."""
        if self.target_value == 0:
            # If target is 0, progress is 100% if current value is also 0, otherwise it's undefined.
            # We'll treat it as 100% complete to avoid division by zero errors.
            return 100
        
        # Calculate progress as a percentage
        progress = (self.current_value / self.target_value) * 100
        
        # Ensure progress doesn't exceed 100%
        return min(progress, 100)

