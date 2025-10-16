# app.py

from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# --- Configuration ---
app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///campus.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_super_secret_key_123' 

db = SQLAlchemy(app)

# =================================================================
# --- Database Models (Tables) ---
# =================================================================

class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    enrollments = db.relationship('Enrollment', backref='student', lazy=True)
    
class Club(db.Model):
    club_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    summary = db.Column(db.String(250), nullable=False)
    description = db.Column(db.Text, nullable=True)
    faculty_advisor = db.Column(db.String(100), nullable=True)
    photo_url = db.Column(db.String(200), nullable=True)
    past_events_summary = db.Column(db.Text, nullable=True)
    events = db.relationship('Event', backref='club', lazy=True)
    updates = db.relationship('Update', backref='club', lazy=True)
    enrollments = db.relationship('Enrollment', backref='club', lazy=True)

class Coordinator(db.Model):
    coord_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey('club.club_id'), unique=True, nullable=False)
    user = db.relationship('User', backref='coordination', uselist=False)
    club = db.relationship('Club', backref='coordinator', uselist=False)

class Event(db.Model):
    event_id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey('club.club_id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    date_time = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    registration_link = db.Column(db.String(200), nullable=True)

class Update(db.Model):
    update_id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey('club.club_id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.now())

class Enrollment(db.Model):
    enrollment_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    club_id = db.Column(db.Integer, db.ForeignKey('club.club_id'), nullable=False)
    status = db.Column(db.String(20), default='Applicant') # 'Applicant' or 'Member'
    __table_args__ = (db.UniqueConstraint('student_id', 'club_id', name='_student_club_uc'),)

class Notification(db.Model):
    notification_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.now())
    is_read = db.Column(db.Boolean, default=False)

class EventRegistration(db.Model):
    registration_id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.event_id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    registration_date = db.Column(db.DateTime, default=db.func.now())
    
    student_roll_number = db.Column(db.String(50), nullable=False)
    contact_email = db.Column(db.String(120), nullable=True)
    contact_phone = db.Column(db.String(50), nullable=True)
    
    student_year = db.Column(db.String(20), nullable=True) 
    student_major = db.Column(db.String(100), nullable=True)
    
    event = db.relationship('Event', backref='registrations', lazy=True)
    student = db.relationship('User', backref='event_registrations', lazy=True)
    
    __table_args__ = (db.UniqueConstraint('event_id', 'student_id', name='_event_student_uc'),)
# =================================================================
# --- Helper Functions ---
# =================================================================

def requires_coordinator_access(club_id):
    """Helper function to verify the logged-in user is the coordinator for the given club."""
    if 'role' not in session or session['role'] != 'Coordinator':
        return False, "Access Denied: Must be a Coordinator."
        
    coord_link = Coordinator.query.filter_by(coord_id=session['user_id']).first()
    
    if not coord_link or coord_link.club_id != club_id:
        return False, "Access Denied: You do not coordinate this club."
        
    return True, Club.query.get_or_404(club_id)


# =================================================================
# --- Authentication & Core Routes ---
# =================================================================

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html', error=request.args.get('error'))

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    user = User.query.filter_by(username=username).first()

    if user and user.password_hash == password: 
        session['user_id'] = user.user_id
        session['role'] = user.role
        return redirect(url_for('dashboard'))
    
    return redirect(url_for('index', error='Invalid username or password.'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)
    return redirect(url_for('index'))


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    role = session['role']
    user_id = session['user_id']
    
    if role == 'Student':
        clubs = Club.query.all()
        events = Event.query.join(Club).order_by(Event.date_time.desc()).all()
        club_updates = Update.query.join(Club).order_by(Update.timestamp.desc()).all()
        personal_notifications = Notification.query.filter_by(user_id=user_id).order_by(Notification.timestamp.desc()).all()
        
        my_enrollments = Enrollment.query.filter_by(student_id=user_id).join(Club).all()
        
        my_memberships = [e for e in my_enrollments if e.status == 'Member']
        my_applications = [e for e in my_enrollments if e.status == 'Applicant']

        return render_template(
            'student_dashboard.html', 
            clubs=clubs, 
            events=events, 
            updates=club_updates, 
            personal_notifications=personal_notifications,
            my_memberships=my_memberships,
            my_applications=my_applications
        )
    
    elif role == 'Coordinator':
        coord_link = Coordinator.query.filter_by(coord_id=user_id).first()
        if coord_link:
            club = Club.query.get(coord_link.club_id)
            applicants = Enrollment.query.filter_by(club_id=club.club_id, status='Applicant').all()
            return render_template('coordinator_dashboard.html', club=club, applicants=applicants)
        else:
            return "Coordinator account not linked to a club. Please contact the Admin.", 403
    
    elif role == 'Admin':
        clubs = Club.query.all()
        return render_template('admin_dashboard.html', clubs=clubs)

    return redirect(url_for('index'))

# =================================================================
# --- Student Functionality ---
# =================================================================

@app.route('/club/<int:club_id>')
def club_detail(club_id):
    if 'role' not in session or session['role'] != 'Student':
        return redirect(url_for('index'))
    
    club = Club.query.get_or_404(club_id)
    student_id = session['user_id']
    
    enrollment = Enrollment.query.filter_by(
        student_id=student_id, 
        club_id=club_id
    ).first()
    
    enrollment_status = enrollment.status if enrollment else 'None'
    
    members = Enrollment.query.filter_by(
        club_id=club_id,
        status='Member'
    ).join(User, Enrollment.student_id == User.user_id).all()
    
    return render_template(
        'club_detail.html', 
        club=club, 
        enrollment_status=enrollment_status,
        members=members 
    )

@app.route('/club/<int:club_id>/join', methods=['POST'])
def join_club(club_id):
    if 'role' not in session or session['role'] != 'Student':
        return redirect(url_for('index'))
        
    club = Club.query.get_or_404(club_id)
    student_id = session['user_id']
    
    existing_enrollment = Enrollment.query.filter_by(
        student_id=student_id, 
        club_id=club_id
    ).first()
    
    if existing_enrollment:
        message = f"You have already {existing_enrollment.status.lower()} this club."
        status = 'error'
    else:
        new_enrollment = Enrollment(student_id=student_id, club_id=club_id, status='Applicant')
        db.session.add(new_enrollment)
        db.session.commit()
        message = f"Application sent successfully! Status: Applicant."
        status = 'success'
    
    return render_template('club_detail.html', club=club, enrollment_status=new_enrollment.status if 'new_enrollment' in locals() else existing_enrollment.status, message=message, status=status)


@app.route('/register/event/form/<int:event_id>')
def register_event_form(event_id):
    if 'role' not in session or session['role'] != 'Student':
        return redirect(url_for('index'))
    
    event = Event.query.get_or_404(event_id)
    student_id = session['user_id']
    
    existing_reg = EventRegistration.query.filter_by(
        event_id=event_id, 
        student_id=student_id
    ).first()
    
    if existing_reg:
        error_message = "You are already registered for this event."
    else:
        error_message = None
    
    current_user = User.query.get(student_id)
    
    return render_template(
        'event_register.html', 
        event=event, 
        current_user=current_user,
        error_message=error_message
    )

@app.route('/register/event/submit/<int:event_id>', methods=['POST'])
def register_event_submit(event_id):
    if 'role' not in session or session['role'] != 'Student':
        return redirect(url_for('index'))
    
    event = Event.query.get_or_404(event_id)
    student_id = session['user_id']
    
    existing_reg = EventRegistration.query.filter_by(
        event_id=event_id, 
        student_id=student_id
    ).first()
    
    if existing_reg:
        message = "You were already registered."
        status = 'error'
    else:
        try:
            roll_number = request.form['roll_number']
            contact_email = request.form.get('contact_email')
            contact_phone = request.form.get('contact_phone')
            student_year = request.form.get('student_year')
            student_major = request.form.get('student_major')
            
            new_reg = EventRegistration(
                event_id=event_id, 
                student_id=student_id,
                student_roll_number=roll_number, 
                contact_email=contact_email,    
                contact_phone=contact_phone,
                student_year=student_year,
                student_major=student_major
            )
            db.session.add(new_reg)
            db.session.commit()
            
            notification_message = f"You successfully registered for the '{event.title}' event."
            new_notification = Notification(user_id=student_id, message=notification_message)
            db.session.add(new_notification)
            db.session.commit()
            
            message = "Registration successful! See you there!"
            status = 'success'
        except Exception as e:
            db.session.rollback()
            message = f"An error occurred: {e}"
            status = 'error'

    return redirect(url_for('dashboard', message=message, status=status))
# =================================================================
# --- Admin Functionality ---
# =================================================================

@app.route('/admin/add_club', methods=['POST'])
def add_club():
    if 'role' not in session or session['role'] != 'Admin':
        return redirect(url_for('index'))
    
    message = None
    status = None
    
    try:
        club_name = request.form['club_name']
        summary = request.form['summary']
        description = request.form['description']
        faculty_advisor = request.form['faculty_advisor']
        coord_username = request.form['coord_username']
        coord_password = request.form['coord_password']
        
        if User.query.filter_by(username=coord_username).first():
            raise ValueError(f"Coordinator username '{coord_username}' already exists.")
        if Club.query.filter_by(name=club_name).first():
            raise ValueError(f"Club name '{club_name}' already exists.")

        new_coord_user = User(username=coord_username, password_hash=coord_password, role='Coordinator')
        db.session.add(new_coord_user)
        db.session.flush() 
        
        new_club = Club(
            name=club_name, summary=summary, description=description, 
            faculty_advisor=faculty_advisor,
            past_events_summary="No past events recorded yet."
        )
        db.session.add(new_club)
        db.session.flush() 
        
        new_coord_link = Coordinator(coord_id=new_coord_user.user_id, club_id=new_club.club_id)
        db.session.add(new_coord_link)
        
        db.session.commit()
        
        message = f"Success! Club '{club_name}' created and Coordinator '{coord_username}' assigned."
        status = 'success'
        
    except ValueError as e:
        db.session.rollback() 
        message = str(e)
        status = 'error'
    except Exception as e:
        db.session.rollback() 
        message = f"An unexpected error occurred: {e}"
        status = 'error'

    clubs = Club.query.all()
    return render_template('admin_dashboard.html', clubs=clubs, message=message, status=status)

@app.route('/admin/edit_club/<int:club_id>', methods=['GET', 'POST'])
def admin_edit_club(club_id):
    if 'role' not in session or session['role'] != 'Admin':
        return redirect(url_for('index'))
    
    club = Club.query.get_or_404(club_id)
    message = None
    status = None
    
    if request.method == 'POST':
        try:
            club.summary = request.form['summary']
            club.description = request.form['description']
            club.faculty_advisor = request.form['faculty_advisor']
            club.past_events_summary = request.form['past_events_summary']
            club.photo_url = request.form['photo_url']
            
            db.session.commit()
            message = "Club details updated successfully by Admin!"
            status = 'success'
        except Exception as e:
            db.session.rollback()
            message = f"Error updating club details: {e}"
            status = 'error'

    return render_template('edit_club.html', club=club, message=message, status=status)

@app.route('/admin/delete_club/<int:club_id>', methods=['POST'])
def delete_club(club_id):
    if 'role' not in session or session['role'] != 'Admin':
        return redirect(url_for('index'))

    club = Club.query.get_or_404(club_id)
    club_name = club.name
    
    try:
        Event.query.filter_by(club_id=club_id).delete()
        Update.query.filter_by(club_id=club_id).delete()
        Enrollment.query.filter_by(club_id=club_id).delete()
        Coordinator.query.filter_by(club_id=club_id).delete()
        
        db.session.delete(club)
        db.session.commit()
        
        message = f"Success! Club '{club_name}' and all associated data have been permanently deleted."
        status = 'success'

    except Exception as e:
        db.session.rollback()
        message = f"Error deleting club {club_name}: {e}"
        status = 'error'

    return redirect(url_for('dashboard', message=message, status=status))

@app.route('/admin/manage_users')
def manage_users():
    if 'role' not in session or session['role'] != 'Admin':
        return redirect(url_for('index'))

    users = User.query.filter(User.role != 'Admin').order_by(User.username).all()
    
    message = request.args.get('message')
    status = request.args.get('status')

    return render_template('manage_users.html', users=users, message=message, status=status)


@app.route('/admin/add_user', methods=['POST'])
def add_user():
    if 'role' not in session or session['role'] != 'Admin':
        return redirect(url_for('index'))
        
    username = request.form['username']
    password = request.form['password']
    user_role = request.form['role']
    
    try:
        if User.query.filter_by(username=username).first():
            raise ValueError(f"Username '{username}' already exists.")

        new_user = User(username=username, password_hash=password, role=user_role)
        db.session.add(new_user)
        db.session.commit()
        
        message = f"Success! User '{username}' created with role: {user_role}."
        status = 'success'

    except ValueError as e:
        db.session.rollback()
        message = str(e)
        status = 'error'
    except Exception as e:
        db.session.rollback()
        message = f"An unexpected error occurred: {e}"
        status = 'error'

    return redirect(url_for('manage_users', message=message, status=status))


@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'role' not in session or session['role'] != 'Admin':
        return redirect(url_for('index'))
        
    user_to_delete = User.query.get_or_404(user_id)
    username = user_to_delete.username
    
    if user_to_delete.role == 'Admin':
        return redirect(url_for('manage_users', message="Cannot delete the main admin account.", status='error'))

    try:
        Enrollment.query.filter_by(student_id=user_id).delete()
        EventRegistration.query.filter_by(student_id=user_id).delete()
        Notification.query.filter_by(user_id=user_id).delete()
        Coordinator.query.filter_by(coord_id=user_id).delete()
        
        db.session.delete(user_to_delete)
        db.session.commit()
        
        message = f"Success! User '{username}' and all associated records have been deleted."
        status = 'success'
        
    except Exception as e:
        db.session.rollback()
        message = f"Error deleting user {username}: {e}"
        status = 'error'

    return redirect(url_for('manage_users', message=message, status=status))

# =================================================================
# --- Coordinator Functionality (Corrected Routes) ---
# =================================================================

@app.route('/coord/edit_club/<int:club_id>', methods=['GET', 'POST'])
def edit_club(club_id):
    if 'role' not in session or session['role'] != 'Coordinator':
        return redirect(url_for('index'))
    
    club = Club.query.get_or_404(club_id)
    message = None
    status = None
    
    if request.method == 'POST':
        try:
            club.summary = request.form['summary']
            club.description = request.form['description']
            club.faculty_advisor = request.form['faculty_advisor']
            club.past_events_summary = request.form['past_events_summary']
            club.photo_url = request.form['photo_url']
            
            db.session.commit()
            message = "Club details updated successfully!"
            status = 'success'
        except Exception as e:
            db.session.rollback()
            message = f"Error updating club details: {e}"
            status = 'error'

    return render_template('edit_club.html', club=club, message=message, status=status) 

@app.route('/coord/manage_events/<int:club_id>')
def manage_events(club_id):
    if 'role' not in session or session['role'] != 'Coordinator':
        return redirect(url_for('index'))

    club = Club.query.get_or_404(club_id)
    events = Event.query.filter_by(club_id=club_id).order_by(Event.date_time.asc()).all()
    
    message = request.args.get('message')
    status = request.args.get('status')
    
    return render_template('manage_events.html', club=club, events=events, message=message, status=status)


@app.route('/coord/add_event/<int:club_id>', methods=['POST'])
def add_event(club_id):
    if 'role' not in session or session['role'] != 'Coordinator':
        return redirect(url_for('index'))
        
    club = Club.query.get_or_404(club_id)
    message = None
    status = None
    
    try:
        title = request.form['title']
        location = request.form['location']
        description = request.form['description']
        registration_link = request.form.get('registration_link')
        
        date_time_str = request.form['date_time']
        date_time_obj = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M') 
        
        new_event = Event(
            club_id=club_id, title=title, date_time=date_time_obj, location=location,
            description=description, registration_link=registration_link
        )
        db.session.add(new_event)
        db.session.commit()
        
        message = f"Event '{title}' created successfully!"
        status = 'success'
    except ValueError:
        db.session.rollback()
        message = "Error: Invalid Date/Time format. Use YYYY-MM-DD HH:MM."
        status = 'error'
    except Exception as e:
        db.session.rollback()
        message = f"An error occurred: {e}"
        status = 'error'

    return redirect(url_for('manage_events', club_id=club_id, message=message, status=status))


@app.route('/coord/post_update/<int:club_id>', methods=['GET', 'POST'])
def post_update(club_id):
    if 'role' not in session or session['role'] != 'Coordinator':
        return redirect(url_for('index'))

    club = Club.query.get_or_404(club_id)
    message = None
    status = None

    if request.method == 'POST':
        try:
            message_content = request.form['message']
            new_update = Update(
                club_id=club_id, message=message_content, timestamp=datetime.now()
            )
            db.session.add(new_update)
            db.session.commit()
            
            message = "Update successfully posted to the Student Dashboard!"
            status = 'success'
        except Exception as e:
            db.session.rollback()
            message = f"Error posting update: {e}"
            status = 'error'

    return render_template('post_update.html', club=club, message=message, status=status)

@app.route('/coord/manage_members/<int:club_id>')
def manage_members(club_id):
    if 'role' not in session or session['role'] != 'Coordinator':
        return redirect(url_for('index'))

    club = Club.query.get_or_404(club_id)
    members = Enrollment.query.filter_by(
        club_id=club_id, status='Member'
    ).join(User, Enrollment.student_id == User.user_id).all()
    
    message = request.args.get('message')
    status = request.args.get('status')
    
    return render_template('manage_members.html', club=club, members=members, message=message, status=status)


@app.route('/coord/dismiss_member/<int:enrollment_id>', methods=['POST'])
def dismiss_member(enrollment_id):
    enrollment = Enrollment.query.get_or_404(enrollment_id)
    club_id = enrollment.club_id
    
    club = Club.query.get_or_404(club_id)

    if 'role' not in session or session['role'] != 'Coordinator':
        return redirect(url_for('dashboard'))

    student_username = enrollment.student.username
    student_id = enrollment.student_id
    
    try:
        dismissal_message = f"Your membership in the {club.name} has been dismissed by the coordinator."
        new_notification = Notification(user_id=student_id, message=dismissal_message)
        db.session.add(new_notification)
        
        db.session.delete(enrollment)
        
        db.session.commit()
        
        message = f"Member {student_username} successfully dismissed from {club.name}."
        status = 'success'
    except Exception as e:
        db.session.rollback()
        message = f"Error dismissing member: {e}"
        status = 'error'
    
    return redirect(url_for('manage_members', club_id=club_id, message=message, status=status))


@app.route('/coord/applicants/<int:club_id>')
def review_applicants(club_id):
    if 'role' not in session or session['role'] != 'Coordinator':
        return redirect(url_for('index'))

    club = Club.query.get_or_404(club_id)
    applicants = Enrollment.query.filter_by(
        club_id=club_id, status='Applicant'
    ).join(User, Enrollment.student_id == User.user_id).all()
    
    message = request.args.get('message')
    status = request.args.get('status')
    
    return render_template('review_applicants.html', club=club, applicants=applicants, message=message, status=status)


@app.route('/coord/update_applicant/<int:enrollment_id>', methods=['POST'])
def update_applicant(enrollment_id):
    enrollment = Enrollment.query.get_or_404(enrollment_id)
    club_id = enrollment.club_id
    action = request.form['action']
    
    club = Club.query.get_or_404(club_id)

    if 'role' not in session or session['role'] != 'Coordinator':
        return redirect(url_for('dashboard'))

    student_username = enrollment.student.username
    student_id = enrollment.student_id
    
    try:
        if action == 'enroll':
            enrollment.status = 'Member'
            message = f"Student {student_username} successfully enrolled in {club.name}!"
            status = 'success'
        elif action == 'reject':
            rejection_message = f"Your application to join the {club.name} has been rejected."
            new_notification = Notification(user_id=student_id, message=rejection_message)
            db.session.add(new_notification)
            db.session.delete(enrollment)
            message = f"Student {student_username}'s application to {club.name} was rejected."
            status = 'error' 
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        message = f"Error processing action: {e}"
        status = 'error'
    
    return redirect(url_for('review_applicants', club_id=club_id, message=message, status=status))

@app.route('/coord/view_registrations/<int:event_id>')
def view_registrations(event_id):
    if 'role' not in session or session['role'] != 'Coordinator':
        return redirect(url_for('index'))

    event = Event.query.get_or_404(event_id)
    club_id = event.club_id

    if 'role' not in session or session['role'] != 'Coordinator':
        return redirect(url_for('dashboard'))

    registrations = EventRegistration.query.filter_by(
        event_id=event_id
    ).join(User, EventRegistration.student_id == User.user_id).all()
    
    message = request.args.get('message')
    status = request.args.get('status')
    
    return render_template('view_registrations.html', event=event, registrations=registrations, message=message, status=status)

# =================================================================
# --- Database Initialization Command (For Setup) ---
# =================================================================
@app.cli.command('init-db')
def init_db():
    """Initializes the database and adds mock data, including 50 extra students."""
    db.drop_all() 
    db.create_all() 
    
    # --- Mock Data Insertion ---
    
    # 1. Base Users (Admin, Coordinator, Student1, Student2)
    admin_user = User(username='admin', password_hash='123', role='Admin')
    coord_user = User(username='coord', password_hash='123', role='Coordinator')
    student_user1 = User(username='student1', password_hash='123', role='Student')
    student_user2 = User(username='student2', password_hash='123', role='Student')
    
    users_to_add = [admin_user, coord_user, student_user1, student_user2]

    # NEW: Loop to add 50 extra student users (student3 to student53)
    for i in range(3, 54): # This range includes 3 and excludes 54 (giving us 51 total students)
        username = f'student{i}'
        new_student = User(username=username, password_hash='123', role='Student')
        users_to_add.append(new_student)
        
    db.session.add_all(users_to_add)
    db.session.commit()
    
    # Get the user ID for student1 for enrollment mocking
    # NOTE: We use student_user1 to reference the ID of the initially created student.
    student1_user_id = student_user1.user_id

    # 2. Club
    tech_club = Club(
        name='Tech Innovators Club', 
        summary='Focuses on app development, AI, and hackathons.',
        description='A club for students passionate about technology and innovation. We meet weekly for coding sessions and guest lectures.',
        faculty_advisor='Dr. A. Sharma',
        past_events_summary='Successfully hosted the Annual Hackathon in March.',
        photo_url='/static/img/tech_club_default.jpg'
    )
    db.session.add(tech_club)
    db.session.commit()
    
    # 3. Coordinator Link
    coord_link = Coordinator(coord_id=coord_user.user_id, club_id=tech_club.club_id)
    db.session.add(coord_link)
    
    # 4. Event
    event_1 = Event(
        club_id=tech_club.club_id, 
        title='Annual Coding Competition', 
        date_time=datetime(2025, 11, 15, 10, 0), 
        location='Auditorium',
        description='Solve challenges and win prizes!',
        registration_link='/register/codecomp'
    )
    db.session.add(event_1)
    
    # 5. Update
    update_1 = Update(
        club_id=tech_club.club_id, 
        message='New meeting schedule posted. Check the club page.',
        timestamp=datetime.now()
    )
    db.session.add(update_1)

    # 6. Enrollment (Student1 is an applicant)
    enroll_1 = Enrollment(
        student_id=student1_user_id, 
        club_id=tech_club.club_id, 
        status='Applicant'
    )
    db.session.add(enroll_1)
    
    db.session.commit()
    print("Database initialized, tables created, and 53 user accounts inserted!")

if __name__ == '__main__':
    app.run(debug=True)