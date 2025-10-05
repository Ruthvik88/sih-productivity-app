from datetime import datetime
from app import db
from werkzeug.security import generate_password_hash, check_password_hash

# --- NEW: Define the league structure and thresholds ---
LEAGUES = {
    'Bronze': {'min_score': 0, 'next_league': 'Silver'},
    'Silver': {'min_score': 50, 'next_league': 'Gold'},
    'Gold': {'min_score': 70, 'next_league': 'Diamond'},
    'Diamond': {'min_score': 90, 'next_league': None} # Top league
}

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(64), index=True, default='Employee')
    
    # --- NEW: Add the league column to the User model ---
    league = db.Column(db.String(64), index=True, default='Bronze', nullable=False)

    manager_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    goals = db.relationship('Goal', backref='employee', lazy='dynamic')
    reports = db.relationship('User', backref=db.backref('manager', remote_side=[id]), lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def calculate_performance_score(self):
        my_goals = self.goals.all()
        if not my_goals:
            return 0

        total_weighted_progress = sum(goal.get_progress() * goal.weight for goal in my_goals)
        total_weight = sum(goal.weight for goal in my_goals)

        if total_weight == 0:
            return 0
            
        final_score = int((total_weighted_progress / total_weight))
        return final_score
        
    # --- NEW: Method to check for and apply promotions ---
    def update_league(self):
        """Checks user's score and promotes them to the next league if they qualify."""
        score = self.calculate_performance_score()
        current_league_info = LEAGUES.get(self.league)
        
        # Don't do anything if they are already in the top league
        if not current_league_info or not current_league_info['next_league']:
            return

        next_league_name = current_league_info['next_league']
        next_league_info = LEAGUES.get(next_league_name)

        if score >= next_league_info['min_score']:
            self.league = next_league_name
            db.session.commit()
            # We can add a flash message or notification here in a future version
            print(f"User {self.full_name} promoted to {next_league_name} league!")

    def __repr__(self):
        return f'<User {self.full_name}>'

class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    description = db.Column(db.Text)
    kpi_name = db.Column(db.String(100))
    current_value = db.Column(db.Integer, default=0)
    target_value = db.Column(db.Integer, default=100, nullable=False)
    weight = db.Column(db.Integer, default=5, nullable=False, server_default='5')
    status = db.Column(db.String(64), index=True, default='In Progress')
    due_date = db.Column(db.DateTime)
    manager_feedback = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def get_progress(self):
        """Calculates the percentage progress towards the target value."""
        if self.target_value == 0:
            return 100 if self.current_value > 0 else 0
        progress = (self.current_value / self.target_value) * 100
        return min(progress, 100) # Cap progress at 100%

    def __repr__(self):
        return f'<Goal {self.title}>'

