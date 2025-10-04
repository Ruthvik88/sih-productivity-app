from app import app, db
from app.models import User, Goal

def seed_data():
    """
    Clears existing data and populates the database with sample users and goals.
    """
    with app.app_context():
        # --- Step 1: Clear all existing data ---
        # The order is important to avoid foreign key constraint errors.
        # Goals must be deleted before users.
        print("Clearing existing data...")
        db.session.query(Goal).delete()
        db.session.query(User).delete()
        print("Data cleared.")

        # --- Step 2: Create the users ---
        print("Creating new users...")
        # Administrator
        admin = User(
            full_name='Admin User', 
            email='admin@gov.in', 
            role='Administrator'
        )
        admin.set_password('adminpass')

        # Manager
        manager1 = User(
            full_name='Manager One', 
            email='manager.one@gov.in', 
            role='Manager'
        )
        manager1.set_password('managerpass')

        # Employees who report to Manager One
        employee1 = User(
            full_name='Employee One', 
            email='employee.one@gov.in', 
            role='Employee', 
            manager=manager1
        )
        employee1.set_password('emppass1')
        
        employee2 = User(
            full_name='Employee Two', 
            email='employee.two@gov.in', 
            role='Employee', 
            manager=manager1
        )
        # --- THIS IS THE CHANGE ---
        # Giving the second employee a different password
        employee2.set_password('emppass2')

        # Add users to the session
        db.session.add_all([admin, manager1, employee1, employee2])
        db.session.commit() # Commit to assign IDs to the users
        print("Users created successfully.")

        # --- Step 3: Create and assign goals ---
        print("Creating and assigning goals...")
        goal1_emp1 = Goal(
            title='Prepare Quarterly Financial Report',
            description='Compile financial data from all departments for the Q3 report.',
            kpi_name='Report Accuracy',
            target_value=98, # Target is 98% accuracy
            current_value=50,
            weight=10,
            employee=employee1
        )

        goal2_emp1 = Goal(
            title='Process pending administrative files',
            kpi_name='Files Cleared',
            target_value=50,
            current_value=10,
            weight=5,
            employee=employee1
        )
        
        goal1_emp2 = Goal(
            title='Conduct field survey for New Project Alpha',
            description='Complete the initial land survey and submit the preliminary findings.',
            kpi_name='Survey Timeliness',
            target_value=100,
            current_value=75,
            status='In Progress',
            weight=8,
            employee=employee2
        )

        goal2_emp2 = Goal(
            title='Update Project Documentation',
            kpi_name='Documents Updated',
            target_value=25,
            current_value=25,
            status='Completed',
            weight=3,
            employee=employee2
        )

        # Add goals to the session
        db.session.add_all([goal1_emp1, goal2_emp1, goal1_emp2, goal2_emp2])
        db.session.commit()
        print("Goals created successfully.")
        print("-" * 20)
        print("Database seeding complete!")
        print("You can now log in with the sample accounts.")

# This allows the script to be run from the command line
if __name__ == '__main__':
    seed_data()

