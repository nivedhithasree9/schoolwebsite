import json
import os
import secrets
import csv
import io
from functools import wraps

try:
    import mysql.connector
    from mysql.connector import Error
except ImportError as import_error:
    print("Missing package: mysql-connector-python")
    print("Run: pip install -r requirements.txt")
    raise SystemExit(1) from import_error

try:
    from flask import Flask, jsonify, request, Response
except ImportError as import_error:
    print("Missing package: Flask")
    print("Run: pip install -r requirements.txt")
    raise SystemExit(1) from import_error


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "db_config.json")

app = Flask(__name__)

ALLOWED_ORIGINS = {
    "http://127.0.0.1:5500",
    "http://localhost:5500",
}

active_sessions = {}


def generate_student_unique_id():
    return f"{secrets.randbelow(900000) + 100000}"


def compute_fee_details(class_name):
    normalized_class = str(class_name or "6")
    total_fee = max(18000, 22000 + len(normalized_class) * 1200)
    paid_amount = int(total_fee * 0.72)
    due_amount = total_fee - paid_amount
    pending_fine = 250 if due_amount > 0 else 0
    return {
        "total_fee": total_fee,
        "paid_amount": paid_amount,
        "due_amount": due_amount,
        "pending_fine": pending_fine,
    }


def load_db_config():
    default_config = {
        "host": "localhost",
        "port": 3306,
        "database": "school_management",
        "user": "root",
        "password": "root123",
    }

    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w", encoding="utf-8") as file:
            json.dump(default_config, file, indent=2)
        return default_config

    with open(CONFIG_PATH, "r", encoding="utf-8") as file:
        file_config = json.load(file)

    return {
        "host": file_config.get("host", default_config["host"]),
        "port": int(file_config.get("port", default_config["port"])),
        "database": file_config.get("database", default_config["database"]),
        "user": file_config.get("user", default_config["user"]),
        "password": file_config.get("password", default_config["password"]),
    }


DB_CONFIG = load_db_config()


def json_error(message, status_code=400):
    return jsonify({"success": False, "message": message}), status_code


def add_cors_headers(response):
    origin = request.headers.get("Origin", "")
    if is_allowed_origin(origin):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Admin-Token, X-Student-Token"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Vary"] = "Origin"
    return response


def is_allowed_origin(origin):
    if not origin:
        return False

    if origin in ALLOWED_ORIGINS:
        return True

    if origin == "null":
        # Allow opening HTML files directly via file:// during local development.
        return True

    return origin.startswith("http://127.0.0.1:") or origin.startswith("http://localhost:")


@app.after_request
def after_request(response):
    return add_cors_headers(response)


@app.route("/api/<path:_path>", methods=["OPTIONS"])
def options_handler(_path):
    return ("", 204)


def admin_required(handler):
    @wraps(handler)
    def wrapper(*args, **kwargs):
        token = request.headers.get("X-Admin-Token", "").strip()
        session = active_sessions.get(token)
        if not session or session.get("role") != "admin":
            return json_error("Unauthorized", 401)
        return handler(*args, **kwargs)

    return wrapper


def student_required(handler):
    @wraps(handler)
    def wrapper(*args, **kwargs):
        token = request.headers.get("X-Student-Token", "").strip()
        session = active_sessions.get(token)
        if not session or session.get("role") != "student":
            return json_error("Unauthorized", 401)
        return handler(*args, **kwargs)

    return wrapper


def get_connection(use_database=True):
    config = {
        "host": DB_CONFIG["host"],
        "port": DB_CONFIG["port"],
        "user": DB_CONFIG["user"],
        "password": DB_CONFIG["password"],
    }

    if use_database:
        config["database"] = DB_CONFIG["database"]

    return mysql.connector.connect(**config)


def execute_query(query, values=None, fetch=False, fetchone=False, dictionary=False):
    connection = get_connection()
    cursor = connection.cursor(dictionary=dictionary)

    try:
        cursor.execute(query, values or ())

        if fetchone:
            result = cursor.fetchone()
        elif fetch:
            result = cursor.fetchall()
        else:
            result = None

        connection.commit()
        return result
    finally:
        cursor.close()
        connection.close()


def init_database():
    try:
        root_connection = get_connection(use_database=False)
        root_cursor = root_connection.cursor()
        root_cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}`")
        root_connection.commit()
        root_cursor.close()
        root_connection.close()

        execute_query(
            """
            CREATE TABLE IF NOT EXISTS admin_users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL
            )
            """
        )

        execute_query(
            """
            CREATE TABLE IF NOT EXISTS notices (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(150) NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        execute_query(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_unique_id VARCHAR(20) UNIQUE,
                name VARCHAR(100) NOT NULL,
                gender VARCHAR(20) NOT NULL,
                dob DATE DEFAULT NULL,
                aadhaar CHAR(12) NOT NULL,
                phone CHAR(10) NOT NULL,
                father VARCHAR(100) DEFAULT '',
                focc VARCHAR(100) DEFAULT '',
                faadhaar CHAR(12) DEFAULT '',
                mother VARCHAR(100) DEFAULT '',
                mocc VARCHAR(100) DEFAULT '',
                maadhaar CHAR(12) DEFAULT '',
                school VARCHAR(150) DEFAULT '',
                class_name VARCHAR(50) DEFAULT '',
                medium VARCHAR(50) DEFAULT '',
                nation VARCHAR(100) DEFAULT '',
                state_name VARCHAR(100) DEFAULT '',
                religion VARCHAR(100) DEFAULT '',
                caste VARCHAR(100) DEFAULT '',
                remarks TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        existing_column = execute_query(
            "SHOW COLUMNS FROM students LIKE 'student_unique_id'",
            fetchone=True,
            dictionary=True,
        )
        if not existing_column:
            execute_query("ALTER TABLE students ADD COLUMN student_unique_id VARCHAR(20) UNIQUE")

        dob_column = execute_query(
            "SHOW COLUMNS FROM students LIKE 'dob'",
            fetchone=True,
            dictionary=True,
        )
        if not dob_column:
            execute_query("ALTER TABLE students ADD COLUMN dob DATE DEFAULT NULL")

        existing_students = execute_query(
            "SELECT id FROM students WHERE student_unique_id IS NULL OR student_unique_id = ''",
            fetch=True,
            dictionary=True,
        ) or []
        for student in existing_students:
            execute_query(
                "UPDATE students SET student_unique_id = %s WHERE id = %s",
                (f"{100000 + int(student['id']):06d}", student["id"]),
            )

        students_without_dob = execute_query(
            "SELECT id FROM students WHERE dob IS NULL",
            fetch=True,
            dictionary=True,
        ) or []
        for student in students_without_dob:
            day = 10 + (int(student["id"]) % 18)
            execute_query(
                "UPDATE students SET dob = %s WHERE id = %s",
                (f"2014-08-{day:02d}", student["id"]),
            )

        execute_query(
            """
            INSERT INTO admin_users (username, password)
            SELECT 'admin', '1234'
            WHERE NOT EXISTS (
                SELECT 1 FROM admin_users WHERE username = 'admin'
            )
            """
        )
        execute_query(
            """
            INSERT INTO notices (title, message)
            SELECT 'Fee Reminder', 'Students with pending activity fee should complete payment this week.'
            WHERE NOT EXISTS (
                SELECT 1 FROM notices WHERE title = 'Fee Reminder'
            )
            """
        )
    except Error as error:
        print("")
        print("MySQL connection failed.")
        print(f"Reason: {error}")
        print(f"Check database settings in {CONFIG_PATH}")
        raise SystemExit(1) from error


@app.route("/api/login", methods=["POST"])
def login():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", "")).strip()

    if not username or not password:
        return json_error("Username and password are required.", 422)

    admin = execute_query(
        "SELECT id FROM admin_users WHERE username = %s AND password = %s LIMIT 1",
        (username, password),
        fetchone=True,
        dictionary=True,
    )

    if not admin:
        return json_error("Wrong username or password.", 401)

    token = secrets.token_hex(16)
    active_sessions[token] = {"role": "admin", "admin_id": admin["id"]}
    return jsonify({"success": True, "token": token})


@app.route("/api/logout", methods=["POST"])
@admin_required
def logout():
    token = request.headers.get("X-Admin-Token", "").strip()
    active_sessions.pop(token, None)
    return jsonify({"success": True})


@app.route("/api/student_login", methods=["POST"])
def student_login():
    payload = request.get_json(silent=True) or {}
    login_id = str(payload.get("login_id", "")).strip()
    dob = str(payload.get("dob", "")).strip()

    if not login_id or not dob:
        return json_error("Student ID or phone number and DOB are required.", 422)

    student = execute_query(
        """
        SELECT *
        FROM students
        WHERE (student_unique_id = %s OR phone = %s) AND dob = %s
        LIMIT 1
        """,
        (login_id, login_id, dob),
        fetchone=True,
        dictionary=True,
    )

    if not student:
        return json_error("Student login details are incorrect.", 401)

    token = secrets.token_hex(16)
    active_sessions[token] = {"role": "student", "student_id": student["id"]}
    return jsonify({
        "success": True,
        "token": token,
        "student_name": student["name"],
    })


@app.route("/api/student_logout", methods=["POST"])
@student_required
def student_logout():
    token = request.headers.get("X-Student-Token", "").strip()
    active_sessions.pop(token, None)
    return jsonify({"success": True})


@app.route("/api/create_student", methods=["POST"])
def create_student():
    payload = request.get_json(silent=True) or {}

    data = {
        "student_unique_id": generate_student_unique_id(),
        "name": str(payload.get("name", "")).strip(),
        "gender": str(payload.get("gender", "")).strip(),
        "dob": str(payload.get("dob", "")).strip(),
        "aadhaar": str(payload.get("aadhaar", "")).strip(),
        "phone": str(payload.get("phone", "")).strip(),
        "father": str(payload.get("father", "")).strip(),
        "focc": str(payload.get("focc", "")).strip(),
        "faadhaar": str(payload.get("faadhaar", "")).strip(),
        "mother": str(payload.get("mother", "")).strip(),
        "mocc": str(payload.get("mocc", "")).strip(),
        "maadhaar": str(payload.get("maadhaar", "")).strip(),
        "school": str(payload.get("school", "")).strip(),
        "class_name": str(payload.get("class_name", "")).strip(),
        "medium": str(payload.get("medium", "")).strip(),
        "nation": str(payload.get("nation", "")).strip(),
        "state_name": str(payload.get("state_name", "")).strip(),
        "religion": str(payload.get("religion", "")).strip(),
        "caste": str(payload.get("caste", "")).strip(),
        "remarks": str(payload.get("remarks", "")).strip(),
    }

    if not data["name"]:
        return json_error("Name is required.", 422)
    if not data["dob"]:
        return json_error("Date of birth is required.", 422)
    if not data["aadhaar"].isdigit() or len(data["aadhaar"]) != 12:
        return json_error("Aadhaar must be 12 digits.", 422)
    if not data["phone"].isdigit() or len(data["phone"]) != 10:
        return json_error("Phone must be 10 digits.", 422)

    execute_query(
        """
        INSERT INTO students (
            student_unique_id, name, gender, dob, aadhaar, phone, father, focc, faadhaar, mother, mocc, maadhaar,
            school, class_name, medium, nation, state_name, religion, caste, remarks
        ) VALUES (
            %(student_unique_id)s, %(name)s, %(gender)s, %(dob)s, %(aadhaar)s, %(phone)s, %(father)s, %(focc)s, %(faadhaar)s,
            %(mother)s, %(mocc)s, %(maadhaar)s, %(school)s, %(class_name)s, %(medium)s,
            %(nation)s, %(state_name)s, %(religion)s, %(caste)s, %(remarks)s
        )
        """,
        data,
    )

    return jsonify({
        "success": True,
        "message": "Saved successfully.",
        "student_unique_id": data["student_unique_id"],
    })


@app.route("/api/get_students", methods=["GET"])
@admin_required
def get_students():
    students = execute_query(
        "SELECT * FROM students ORDER BY id DESC",
        fetch=True,
        dictionary=True,
    )
    return jsonify({"success": True, "students": students})


@app.route("/api/due_members", methods=["GET"])
@admin_required
def due_members():
    students = execute_query(
        "SELECT * FROM students ORDER BY id DESC",
        fetch=True,
        dictionary=True,
    ) or []
    members = []
    for student in students:
        fee_info = compute_fee_details(student.get("class_name"))
        if fee_info["due_amount"] > 0:
            members.append({
                "student_unique_id": student.get("student_unique_id"),
                "name": student.get("name"),
                "class_name": student.get("class_name"),
                "phone": student.get("phone"),
                "due_amount": fee_info["due_amount"],
                "fine_amount": fee_info["pending_fine"],
            })
    return jsonify({"success": True, "members": members})


@app.route("/api/notices", methods=["GET"])
@admin_required
def get_notices():
    notices = execute_query(
        "SELECT * FROM notices ORDER BY id DESC LIMIT 10",
        fetch=True,
        dictionary=True,
    ) or []
    return jsonify({"success": True, "notices": notices})


@app.route("/api/notices", methods=["POST"])
@admin_required
def create_notice():
    payload = request.get_json(silent=True) or {}
    title = str(payload.get("title", "")).strip()
    message = str(payload.get("message", "")).strip()

    if not title or not message:
        return json_error("Notice title and message are required.", 422)

    execute_query(
        "INSERT INTO notices (title, message) VALUES (%s, %s)",
        (title, message),
    )
    return jsonify({"success": True, "message": "Notice published successfully."})


@app.route("/api/public_notices", methods=["GET"])
def public_notices():
    notices = execute_query(
        "SELECT * FROM notices ORDER BY id DESC LIMIT 5",
        fetch=True,
        dictionary=True,
    ) or []
    return jsonify({"success": True, "notices": notices})


def build_student_dashboard(student):
    class_name = str(student.get("class_name") or "6")
    medium = student.get("medium") or "English"
    fee_base = max(18000, 22000 + len(class_name) * 1200)
    paid = int(fee_base * 0.72)
    due = fee_base - paid
    fine = 250 if due > 0 else 0
    attendance_records = [
        {"date": "2026-04-07", "day": "Tuesday", "period": "09:30-10:15", "subject": "Mathematics", "status": "Present"},
        {"date": "2026-04-07", "day": "Tuesday", "period": "10:15-11:00", "subject": "Science", "status": "Present"},
        {"date": "2026-04-07", "day": "Tuesday", "period": "11:15-12:00", "subject": "English", "status": "Absent"},
        {"date": "2026-04-06", "day": "Monday", "period": "09:30-10:15", "subject": "Social", "status": "Present"},
        {"date": "2026-04-06", "day": "Monday", "period": "10:15-11:00", "subject": medium, "status": "Present"},
        {"date": "2026-04-05", "day": "Sunday", "period": "10:00-10:45", "subject": "Mathematics", "status": "Absent"},
        {"date": "2026-04-04", "day": "Saturday", "period": "09:30-10:15", "subject": "Science", "status": "Present"},
        {"date": "2026-04-04", "day": "Saturday", "period": "10:15-11:00", "subject": "English", "status": "Present"},
    ]
    subjects = [
        {
            "name": "Mathematics",
            "teacher": "Mrs. Kavitha",
            "attendance": 92,
            "marks": 88,
            "homework": "Complete practice set 5 and revise fractions.",
            "missed_topic": "Word problems on real-life budgeting",
        },
        {
            "name": "Science",
            "teacher": "Mr. Pradeep",
            "attendance": 89,
            "marks": 84,
            "homework": "Draw and label the human digestive system.",
            "missed_topic": "Photosynthesis experiment observation",
        },
        {
            "name": "English",
            "teacher": "Ms. Harini",
            "attendance": 95,
            "marks": 90,
            "homework": "Write a paragraph on your school assembly.",
            "missed_topic": "Poem explanation and recitation practice",
        },
        {
            "name": "Social",
            "teacher": "Mr. Sandeep",
            "attendance": 87,
            "marks": 79,
            "homework": "Prepare notes on Indian rivers and dams.",
            "missed_topic": "Map pointing activity",
        },
        {
            "name": medium,
            "teacher": "Mrs. Bhavani",
            "attendance": 91,
            "marks": 86,
            "homework": f"Read the next {medium} lesson and underline new words.",
            "missed_topic": f"{medium} reading circle discussion",
        },
    ]
    timetable = [
        {"day": "Monday", "slots": ["Assembly", "Mathematics", "Science", "English", "Games"]},
        {"day": "Tuesday", "slots": ["Assembly", "Social", medium, "Mathematics", "Library"]},
        {"day": "Wednesday", "slots": ["Assembly", "Science", "English", "Computer", "Sports"]},
        {"day": "Thursday", "slots": ["Assembly", "Mathematics", "Social", medium, "Art"]},
        {"day": "Friday", "slots": ["Assembly", "English", "Science", "Mathematics", "Club Activity"]},
    ]
    missed_classes = [
        {"date": "2026-04-01", "subject": "Science", "topic": "Photosynthesis experiment observation"},
        {"date": "2026-03-27", "subject": "Social", "topic": "Map pointing activity on states"},
    ]
    payments = [
        {"label": "Term 1 Fee", "amount": int(fee_base * 0.36), "status": "Paid"},
        {"label": "Term 2 Fee", "amount": int(fee_base * 0.36), "status": "Paid"},
        {"label": "Activity Fee", "amount": due, "status": "Pending" if due else "Paid"},
    ]
    uniform = {
        "monday_to_thursday": "Sky Blue Shirt + Navy Blue Pant/Skirt",
        "friday": "House T-Shirt + White Bottom",
        "shoes": "Black shoes with white socks",
        "winter": "Navy sweater with school badge",
    }

    return {
        "profile": {
            "student_unique_id": student.get("student_unique_id") or f"{100000 + int(student['id']):06d}",
            "name": student["name"],
            "gender": student["gender"],
            "dob": str(student.get("dob") or ""),
            "class_name": student["class_name"],
            "medium": student["medium"],
            "phone": student["phone"],
            "aadhaar": student["aadhaar"],
            "father": student["father"],
            "mother": student["mother"],
            "school": student["school"],
            "nation": student["nation"],
            "state_name": student["state_name"],
            "religion": student["religion"],
            "caste": student["caste"],
            "remarks": student["remarks"],
            "admission_no": student.get("student_unique_id") or f"{100000 + int(student['id']):06d}",
        },
        "school_overview": {
            "campus": "Taraka Rama Public School, Makkuva",
            "academic_year": "2026-2027",
            "class_teacher": "Mrs. Kavitha",
            "school_timings": "9:00 AM to 4:00 PM",
        },
        "subjects": subjects,
        "attendance_summary": {
            "overall": round(sum(item["attendance"] for item in subjects) / len(subjects)),
            "working_days": 210,
            "attended_days": 192,
            "records": attendance_records,
        },
        "marks_summary": {
            "overall": round(sum(item["marks"] for item in subjects) / len(subjects)),
            "exam": "Quarterly Assessment",
        },
        "fees": {
            "total_fee": fee_base,
            "paid_amount": paid,
            "due_amount": due,
            "payments": payments,
        },
        "fines": {
            "pending_fine": fine,
            "reason": "Late activity fee payment" if fine else "No pending fine",
        },
        "uniform": uniform,
        "timetable": timetable,
        "homeworks": [
            {"subject": item["name"], "task": item["homework"]}
            for item in subjects
        ],
        "missed_classes": missed_classes,
    }


@app.route("/api/student_dashboard", methods=["GET"])
@student_required
def student_dashboard():
    token = request.headers.get("X-Student-Token", "").strip()
    session = active_sessions.get(token, {})
    student_id = session.get("student_id")
    student = execute_query(
        "SELECT * FROM students WHERE id = %s LIMIT 1",
        (student_id,),
        fetchone=True,
        dictionary=True,
    )

    if not student:
        return json_error("Student record not found.", 404)

    return jsonify({
        "success": True,
        "dashboard": build_student_dashboard(student),
    })


@app.route("/api/dashboard_summary", methods=["GET"])
@admin_required
def dashboard_summary():
    total_row = execute_query(
        "SELECT COUNT(*) AS total FROM students",
        fetchone=True,
        dictionary=True,
    ) or {"total": 0}
    boys_row = execute_query(
        "SELECT COUNT(*) AS total FROM students WHERE gender = 'Boy'",
        fetchone=True,
        dictionary=True,
    ) or {"total": 0}
    girls_row = execute_query(
        "SELECT COUNT(*) AS total FROM students WHERE gender = 'Girl'",
        fetchone=True,
        dictionary=True,
    ) or {"total": 0}
    tg_row = execute_query(
        "SELECT COUNT(*) AS total FROM students WHERE gender = 'TG'",
        fetchone=True,
        dictionary=True,
    ) or {"total": 0}
    class_rows = execute_query(
        """
        SELECT class_name, COUNT(*) AS total
        FROM students
        WHERE class_name <> ''
        GROUP BY class_name
        ORDER BY total DESC, class_name ASC
        LIMIT 6
        """,
        fetch=True,
        dictionary=True,
    ) or []
    recent_rows = execute_query(
        """
        SELECT id, name, class_name, created_at
        FROM students
        ORDER BY id DESC
        LIMIT 5
        """,
        fetch=True,
        dictionary=True,
    ) or []

    return jsonify({
        "success": True,
        "summary": {
            "total_students": int(total_row["total"]),
            "boys": int(boys_row["total"]),
            "girls": int(girls_row["total"]),
            "tg": int(tg_row["total"]),
            "class_breakdown": class_rows,
            "recent_admissions": recent_rows,
        }
    })


@app.route("/api/delete_student", methods=["POST"])
@admin_required
def delete_student():
    payload = request.get_json(silent=True) or {}

    try:
        student_id = int(payload.get("id", 0))
    except (TypeError, ValueError):
        return json_error("Invalid student id.", 422)

    if student_id <= 0:
        return json_error("Invalid student id.", 422)

    execute_query("DELETE FROM students WHERE id = %s", (student_id,))
    return jsonify({"success": True})


@app.route("/api/export_students", methods=["GET"])
@admin_required
def export_students():
    students = execute_query(
        "SELECT * FROM students ORDER BY id DESC",
        fetch=True,
        dictionary=True,
    ) or []

    output = io.StringIO()
    fieldnames = [
        "id",
        "name",
        "gender",
        "aadhaar",
        "phone",
        "father",
        "focc",
        "faadhaar",
        "mother",
        "mocc",
        "maadhaar",
        "school",
        "class_name",
        "medium",
        "nation",
        "state_name",
        "religion",
        "caste",
        "remarks",
        "created_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for student in students:
        writer.writerow(student)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=students_export.csv"},
    )


@app.errorhandler(Exception)
def handle_exception(error):
    return json_error(str(error), 500)


if __name__ == "__main__":
    print("Starting server on http://127.0.0.1:8000")
    print(
        f"Using MySQL database '{DB_CONFIG['database']}' on "
        f"{DB_CONFIG['host']}:{DB_CONFIG['port']} as user '{DB_CONFIG['user']}'"
    )
    init_database()
    app.run(host="127.0.0.1", port=8000, debug=True)
