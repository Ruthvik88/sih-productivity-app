from datetime import datetime
from app import db
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(64), index=True, default='Employee')
    league = db.Column(db.String(64), nullable=False, default='Bronze')

    manager_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    goals = db.relationship('Goal', backref='employee', lazy='dynamic')
    reports = db.relationship('User', backref=db.backref('manager', remote_side=[id]), lazy='dynamic')

    # Relationship to the new ProgressUpdate model
    progress_updates = db.relationship('ProgressUpdate', backref='author', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def calculate_performance_score(self):
        my_goals = self.goals.all()
        if not my_goals:
            return 0

        total_weighted_progress = 0
        total_weight = 0

        for goal in my_goals:
            total_weighted_progress += goal.get_progress() * goal.weight
            total_weight += goal.weight

        if total_weight == 0:
            return 0
            
        final_score = int(total_weighted_progress / total_weight)
        return final_score
    
    def update_league(self):
        score = self.calculate_performance_score()
        new_league = self.league # Default to current league
        if score >= 90:
            new_league = 'Diamond'
        elif score >= 75:
            new_league = 'Gold'
        elif score >= 50:
            new_league = 'Silver'
        
        # We won't flash a message here anymore, as it's a background process.
        # The new league will be visible on the next page load.
        if new_league != self.league:
            self.league = new_league
            db.session.commit()

    def __repr__(self):
        return f'<User {self.full_name}>'

class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    description = db.Column(db.Text)
    kpi_name = db.Column(db.String(100))
    current_value = db.Column(db.Integer, default=0)
    target_value = db.Column(db.Integer, nullable=False, default=100)
    weight = db.Column(db.Integer, nullable=False, default=5)
    status = db.Column(db.String(64), index=True, default='In Progress')
    due_date = db.Column(db.DateTime)
    manager_feedback = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationship to the new ProgressUpdate model
    updates = db.relationship('ProgressUpdate', backref='goal', lazy='dynamic', cascade="all, delete-orphan")

    def get_progress(self):
        if self.target_value == 0:
            return 100
        progress_percentage = (self.current_value / self.target_value) * 100
        return min(progress_percentage, 100)

    def __repr__(self):
        return f'<Goal {self.title}>'

# --- NEW MODEL FOR AUDIT TRAIL ---
class ProgressUpdate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    update_value = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)
    proof_url = db.Column(db.String(500)) # e.g., link to a file, e-office number
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    goal_id = db.Column(db.Integer, db.ForeignKey('goal.id'))

    def __repr__(self):
        return f'<ProgressUpdate {self.id} for Goal {self.goal_id}>'

