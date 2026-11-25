
import os
from datetime import datetime, date

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, jsonify
)

from flask_sqlalchemy import SQLAlchemy

from flask_login import (
    LoginManager, UserMixin, login_user,
    logout_user, login_required, current_user
)

from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    "studyiq-local-development-secret"
)

database_url = os.getenv("DATABASE_URL", "sqlite:///studyiq.db")

if database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://", "postgresql://", 1
    )

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# -------------------- DATABASE MODELS --------------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    completed = db.Column(db.Boolean, default=False, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class StudyPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    study_date = db.Column(db.Date, nullable=False)
    duration = db.Column(db.String(30), nullable=False)
    completed = db.Column(db.Boolean, default=False, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


class TimetablePeriod(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(100), nullable=False)
    day = db.Column(db.String(20), nullable=False)
    start_time = db.Column(db.String(5), nullable=False)
    end_time = db.Column(db.String(5), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    level = db.Column(db.String(30), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


# -------------------- LOGIN MANAGER --------------------

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# -------------------- HOME --------------------

@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    return render_template("landing.html")


# -------------------- REGISTER --------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Please fill in all fields.", "error")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
            return redirect(url_for("register"))

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash("Email already registered. Please login.", "error")
            return redirect(url_for("login"))

        new_user = User(
            name=name,
            email=email,
            password=generate_password_hash(password)
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


# -------------------- LOGIN --------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Welcome back!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "error")
        return redirect(url_for("login"))

    return render_template("login.html")


# -------------------- LOGOUT --------------------

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# -------------------- DASHBOARD --------------------

@app.route("/dashboard")
@login_required
def dashboard():
    tasks = Task.query.filter_by(
        user_id=current_user.id
    ).order_by(Task.created_at.desc()).all()

    total_tasks = Task.query.filter_by(
        user_id=current_user.id
    ).count()

    completed_tasks = Task.query.filter_by(
        user_id=current_user.id,
        completed=True
    ).count()

    progress = (
        int((completed_tasks / total_tasks) * 100)
        if total_tasks > 0 else 0
    )

    return render_template(
        "dashboard.html",
        tasks=tasks,
        progress=progress,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks
    )


# -------------------- TASK ROUTES --------------------

@app.route("/add-task", methods=["POST"])
@login_required
def add_task():
    title = request.form.get("title", "").strip()

    if not title:
        flash("Please enter a task title.", "error")
        return redirect(url_for("dashboard"))

    new_task = Task(
        title=title,
        user_id=current_user.id
    )

    db.session.add(new_task)
    db.session.commit()

    return redirect(url_for("dashboard"))


@app.route("/complete-task/<int:task_id>", methods=["POST"])
@login_required
def complete_task(task_id):
    task = Task.query.filter_by(
        id=task_id,
        user_id=current_user.id
    ).first_or_404()

    task.completed = True
    db.session.commit()

    return redirect(url_for("dashboard"))


@app.route("/delete-task/<int:task_id>", methods=["POST"])
@login_required
def delete_task(task_id):
    task = Task.query.filter_by(
        id=task_id,
        user_id=current_user.id
    ).first_or_404()

    db.session.delete(task)
    db.session.commit()

    return redirect(url_for("dashboard"))


# -------------------- STUDY PLANNER --------------------

@app.route("/planner")
@login_required
def planner():
    return render_template("planner.html")


@app.route("/api/plans", methods=["GET", "POST"])
@login_required
def study_plans():

    if request.method == "GET":
        plans = StudyPlan.query.filter_by(
            user_id=current_user.id
        ).order_by(StudyPlan.study_date.asc()).all()

        return jsonify([
            {
                "id": plan.id,
                "task": plan.task,
                "subject": plan.subject,
                "date": plan.study_date.isoformat(),
                "duration": plan.duration,
                "completed": plan.completed
            }
            for plan in plans
        ])

    data = request.get_json(silent=True) or {}

    task = str(data.get("task", "")).strip()
    subject = str(data.get("subject", "")).strip()
    study_date = str(data.get("date", "")).strip()
    duration = str(data.get("duration", "")).strip()

    allowed_durations = [
        "30 minutes", "1 hour", "2 hours", "3 hours"
    ]

    if not task or not subject or not study_date or not duration:
        return jsonify({"error": "Please fill in all fields."}), 400

    if len(task) > 200 or len(subject) > 100:
        return jsonify({"error": "Input is too long."}), 400

    if duration not in allowed_durations:
        return jsonify({"error": "Invalid study duration."}), 400

    try:
        parsed_date = date.fromisoformat(study_date)
    except ValueError:
        return jsonify({"error": "Invalid study date."}), 400

    new_plan = StudyPlan(
        task=task,
        subject=subject,
        study_date=parsed_date,
        duration=duration,
        user_id=current_user.id
    )

    db.session.add(new_plan)
    db.session.commit()

    return jsonify({
        "message": "Study plan added successfully!",
        "id": new_plan.id
    }), 201


@app.route("/api/plans/<int:plan_id>", methods=["PATCH", "DELETE"])
@login_required
def manage_study_plan(plan_id):
    plan = StudyPlan.query.filter_by(
        id=plan_id,
        user_id=current_user.id
    ).first_or_404()

    if request.method == "PATCH":
        data = request.get_json(silent=True) or {}

        if data.get("completed") is not True:
            return jsonify({"error": "Invalid update."}), 400

        plan.completed = True
        db.session.commit()

        return jsonify({"message": "Study plan completed!"})

    db.session.delete(plan)
    db.session.commit()

    return jsonify({"message": "Study plan deleted!"})


# -------------------- SUBJECTS --------------------

@app.route("/subjects")
@login_required
def subjects():
    user_subjects = Subject.query.filter_by(
        user_id=current_user.id
    ).order_by(Subject.id.desc()).all()

    return render_template(
        "subjects.html",
        subjects=user_subjects
    )


@app.route("/add-subject", methods=["POST"])
@login_required
def add_subject():
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()

    if not name:
        flash("Please enter a subject name.", "error")
        return redirect(url_for("subjects"))

    subject = Subject(
        name=name,
        description=description,
        user_id=current_user.id
    )

    db.session.add(subject)
    db.session.commit()

    flash("Subject added successfully!", "success")
    return redirect(url_for("subjects"))


@app.route("/delete-subject/<int:subject_id>", methods=["POST"])
@login_required
def delete_subject(subject_id):
    subject = Subject.query.filter_by(
        id=subject_id,
        user_id=current_user.id
    ).first_or_404()

    db.session.delete(subject)
    db.session.commit()

    flash("Subject deleted successfully!", "success")
    return redirect(url_for("subjects"))


# -------------------- TIMETABLE --------------------

@app.route("/timetable")
@login_required
def timetable():
    subjects = Subject.query.filter_by(
        user_id=current_user.id
    ).all()

    periods = TimetablePeriod.query.filter_by(
        user_id=current_user.id
    ).all()

    return render_template(
        "timetable.html",
        subjects=subjects,
        periods=periods
    )


@app.route("/add-period", methods=["POST"])
@login_required
def add_period():
    subject = request.form.get("subject")
    day = request.form.get("day")
    start_time = request.form.get("start_time")
    end_time = request.form.get("end_time")

    valid_days = [
        "Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday"
    ]

    if not all([subject, day, start_time, end_time]):
        flash("Please fill all fields.")
        return redirect(url_for("timetable"))

    if day not in valid_days or start_time >= end_time:
        flash("Please enter valid timetable details.")
        return redirect(url_for("timetable"))

    existing_subject = Subject.query.filter_by(
        name=subject,
        user_id=current_user.id
    ).first()

    if not existing_subject:
        flash("Please select a valid subject.")
        return redirect(url_for("timetable"))

    new_period = TimetablePeriod(
        subject=subject,
        day=day,
        start_time=start_time,
        end_time=end_time,
        user_id=current_user.id
    )

    db.session.add(new_period)
    db.session.commit()

    flash("Timetable period added successfully!")
    return redirect(url_for("timetable"))


@app.route("/delete-period/<int:period_id>", methods=["POST"])
@login_required
def delete_period(period_id):
    period = TimetablePeriod.query.filter_by(
        id=period_id,
        user_id=current_user.id
    ).first_or_404()

    db.session.delete(period)
    db.session.commit()

    flash("Timetable period deleted successfully!")
    return redirect(url_for("timetable"))


# -------------------- MY SKILLS --------------------

@app.route("/my-skills")
@login_required
def my_skills():
    skills = Skill.query.filter_by(
        user_id=current_user.id
    ).all()

    return render_template(
        "my_skills.html",
        skills=skills
    )


@app.route("/add-skill", methods=["POST"])
@login_required
def add_skill():
    name = request.form.get("name", "").strip()
    category = request.form.get("category")
    level = request.form.get("level")

    valid_categories = [
        "Programming", "Technical",
        "Soft Skills", "Design", "Other"
    ]

    valid_levels = [
        "Beginner", "Intermediate", "Advanced"
    ]

    if (
        not name
        or category not in valid_categories
        or level not in valid_levels
    ):
        flash("Please enter valid skill details.")
        return redirect(url_for("my_skills"))

    new_skill = Skill(
        name=name,
        category=category,
        level=level,
        user_id=current_user.id
    )

    db.session.add(new_skill)
    db.session.commit()

    flash("Skill added successfully!")
    return redirect(url_for("my_skills"))


@app.route("/delete-skill/<int:skill_id>", methods=["POST"])
@login_required
def delete_skill(skill_id):
    skill = Skill.query.filter_by(
        id=skill_id,
        user_id=current_user.id
    ).first_or_404()

    db.session.delete(skill)
    db.session.commit()

    flash("Skill deleted successfully!")
    return redirect(url_for("my_skills"))


# -------------------- OPPORTUNITIES --------------------

@app.route("/opportunities")
@login_required
def opportunities():
    return render_template("opportunities.html")


# -------------------- CAREER CENTER --------------------

@app.route("/career-center")
@login_required
def career_center():
    return render_template("career_center.html")


# -------------------- RUN APPLICATION --------------------

with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)
