import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pyodbc
import bcrypt
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)
@app.route('/<path:filename>')
def serve_frontend(filename):
    return send_from_directory(os.path.join(app.root_path, ''), filename)

# --- Configuration ---
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Database Connection ---
CONN_STR = (
    "Driver={SQL Server};"
    "Server=RAKSHIT\SQLEXPRESS;"
    "Database=HRFloDB;"
    "Trusted_Connection=yes;"
)

def get_db_cursor():
    try:
        conn = pyodbc.connect(CONN_STR)
        return conn.cursor()
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

# --- API Endpoints ---

@app.route('/api/register', methods=['POST'])
def register_user():
    data = request.get_json()
    password = data.get('password').encode('utf-8')
    hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())
    user_role = data.get('role', 'Employee')
    cursor = get_db_cursor()
    if not cursor: return jsonify({"message": "Database error"}), 500
    try:
        cursor.execute("INSERT INTO Users (FirstName, LastName, Email, PasswordHash, UserRole) VALUES (?, ?, ?, ?, ?)", (data['firstName'], data['lastName'], data['email'], hashed_password.decode('utf-8'), user_role))
        cursor.connection.commit()
        return jsonify({"message": "User registered successfully!"}), 201
    except pyodbc.IntegrityError:
        return jsonify({"message": "Email already exists."}), 409
    finally:
        if cursor: cursor.connection.close()

@app.route('/api/login', methods=['POST'])
def login_user():
    data = request.get_json()
    cursor = get_db_cursor()
    if not cursor: return jsonify({"message": "Database error"}), 500
    try:
        cursor.execute("SELECT UserID, PasswordHash, UserRole, FirstName, LastName FROM Users WHERE Email = ?", (data['email'],))
        user = cursor.fetchone()
        if user and bcrypt.checkpw(data['password'].encode('utf-8'), user.PasswordHash.encode('utf-8')):
            return jsonify({
                "message": "Login successful!",
                "user": { "id": user.UserID, "role": user.UserRole, "firstName": user.FirstName, "lastName": user.LastName }
            }), 200
        return jsonify({"message": "Invalid email or password."}), 401
    finally:
        if cursor: cursor.connection.close()

# --- NEW: Dashboard Stats Endpoint ---
@app.route('/api/dashboard-stats', methods=['GET'])
def get_dashboard_stats():
    cursor = get_db_cursor()
    if not cursor: return jsonify({"message": "Database error"}), 500
    try:
        # Query for Active Job Postings
        cursor.execute("SELECT COUNT(*) FROM JobPostings WHERE Status = 'Open'")
        active_jobs = cursor.fetchone()[0]
        
        # Query for New Applicants (status 'Received')
        cursor.execute("SELECT COUNT(*) FROM Applications WHERE Status = 'Received'")
        new_applicants = cursor.fetchone()[0]
        
        # Query for Pending Onboarding
        cursor.execute("SELECT COUNT(*) FROM Onboarding WHERE Status = 'Pending'")
        pending_onboarding = cursor.fetchone()[0]

        # Query for Total Employees
        cursor.execute("SELECT COUNT(*) FROM Users WHERE UserRole = 'Employee'")
        total_employees = cursor.fetchone()[0]

        return jsonify({
            "activeJobPostings": active_jobs,
            "candidatesInPipeline": new_applicants,
            "pendingOnboarding": pending_onboarding,
            "totalEmployees": total_employees
        })
    except Exception as e:
        print(f"Error fetching dashboard stats: {e}")
        return jsonify({"message": "An error occurred while fetching stats."}), 500
    finally:
        if cursor: cursor.connection.close()
        
# ... (All other endpoints remain the same) ...
@app.route('/api/employees', methods=['GET'])
def get_employees():
    cursor = get_db_cursor()
    if not cursor: return jsonify({"message": "Database error"}), 500
    try:
        cursor.execute("SELECT UserID, FirstName, LastName FROM Users WHERE UserRole = 'Employee' OR UserRole IS NULL")
        employees = [{"userID": r.UserID, "firstName": r.FirstName, "lastName": r.LastName} for r in cursor.fetchall()]
        return jsonify(employees)
    finally:
        if cursor: cursor.connection.close()
    
@app.route('/api/employees/<int:user_id>', methods=['GET'])
def get_employee_details(user_id):
    cursor = get_db_cursor()
    if not cursor: return jsonify({"message": "Database error"}), 500
    try:
        cursor.execute("SELECT FirstName, LastName, Email, Position, Department FROM Users WHERE UserID = ?", (user_id,))
        user = cursor.fetchone()
        if user:
            return jsonify({ "firstName": user.FirstName, "lastName": user.LastName, "email": user.Email, "position": user.Position, "department": user.Department })
        return jsonify({"message": "User not found"}), 404
    finally:
        if cursor: cursor.connection.close()

@app.route('/api/jobs', methods=['GET', 'POST'])
def handle_jobs():
    cursor = get_db_cursor()
    if not cursor: return jsonify({"message": "Database error"}), 500
    try:
        if request.method == 'POST':
            data = request.get_json()
            cursor.execute("INSERT INTO JobPostings (JobTitle, JobDescription, Location, Department, EmploymentType, ClosingDate) VALUES (?, ?, ?, ?, ?, ?)",(data['jobTitle'], data['jobDescription'], data['location'], data['department'], data['employmentType'], data['closingDate']))
            cursor.connection.commit()
            return jsonify({"message": "Job created!"}), 201
        
        cursor.execute("SELECT JobID, JobTitle, Department, Status, ClosingDate FROM JobPostings WHERE Status = 'Open'")
        jobs = [{"jobID": r.JobID, "title": r.JobTitle, "department": r.Department, "status": r.Status, "closingDate": r.ClosingDate} for r in cursor.fetchall()]
        return jsonify(jobs)
    finally:
        if cursor: cursor.connection.close()

@app.route('/api/apply', methods=['POST'])
def apply_for_job():
    data = request.get_json()
    cursor = get_db_cursor()
    if not cursor: return jsonify({"message": "Database error"}), 500
    try:
        cursor.execute("SELECT CandidateID FROM Candidates WHERE Email = ?", (data['email'],))
        candidate = cursor.fetchone()
        if not candidate:
            cursor.execute("INSERT INTO Candidates (FullName, Email, Resume) OUTPUT INSERTED.CandidateID VALUES (?, ?, ?)", (data['name'], data['email'], data.get('resume')))
            candidate_id = cursor.fetchone()[0]
        else:
            candidate_id = candidate.CandidateID
        cursor.execute("INSERT INTO Applications (JobID, CandidateID) VALUES (?, ?)", (data['jobId'], candidate_id))
        cursor.connection.commit()
        return jsonify({"message": "Application submitted!"}), 201
    finally:
        if cursor: cursor.connection.close()
    
@app.route('/api/jobs/<int:job_id>/applicants', methods=['GET'])
def get_job_applicants(job_id):
    cursor = get_db_cursor()
    if not cursor: return jsonify({"message": "Database error"}), 500
    try:
        cursor.execute("SELECT a.ApplicationID, c.FullName, a.Status FROM Applications a JOIN Candidates c ON a.CandidateID = c.CandidateID WHERE a.JobID = ?", (job_id,))
        applicants = [{"id": r.ApplicationID, "name": r.FullName, "status": r.Status} for r in cursor.fetchall()]
        return jsonify(applicants)
    finally:
        if cursor: cursor.connection.close()

@app.route('/api/applications/<int:app_id>/status', methods=['PUT'])
def update_app_status(app_id):
    status = request.get_json()['status']
    cursor = get_db_cursor()
    if not cursor: return jsonify({"message": "Database error"}), 500
    try:
        cursor.execute("UPDATE Applications SET Status = ? WHERE ApplicationID = ?", (status, app_id))
        cursor.connection.commit()
        return jsonify({"message": "Status updated!"})
    finally:
        if cursor: cursor.connection.close()

@app.route('/api/managers', methods=['GET'])
def get_managers():
    cursor = get_db_cursor()
    if not cursor: return jsonify({"message": "Database error"}), 500
    try:
        cursor.execute("SELECT UserID, FirstName, LastName FROM Users WHERE UserRole = 'HR Manager'")
        managers = [{"userID": r.UserID, "firstName": r.FirstName, "lastName": r.LastName} for r in cursor.fetchall()]
        return jsonify(managers)
    finally:
        if cursor: cursor.connection.close()

@app.route('/api/onboarding', methods=['GET', 'POST'])
def handle_onboarding():
    cursor = get_db_cursor()
    if not cursor: return jsonify({"message": "Database error"}), 500
    try:
        if request.method == 'POST':
            data = request.get_json()
            pwd = bcrypt.hashpw('defaultPassword123'.encode('utf-8'), bcrypt.gensalt())
            cursor.execute("INSERT INTO Users (FirstName, LastName, Email, PasswordHash, UserRole, Position, Department, HireDate, ManagerID) OUTPUT INSERTED.UserID VALUES (?, ?, ?, ?, 'Employee', ?, ?, ?, ?)", (data['firstName'], data['lastName'], data['email'], pwd.decode('utf-8'), data['position'], data['department'], data['startDate'], data['managerId']))
            user_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO Onboarding (UserID, StartDate) VALUES (?, ?)", (user_id, data['startDate']))
            cursor.connection.commit()
            return jsonify({"message": "Onboarding created!"}), 201

        cursor.execute("SELECT u.FirstName, u.LastName, u.Department, o.StartDate, o.Status, o.Progress FROM Onboarding o JOIN Users u ON o.UserID = u.UserID")
        onboarding = [{"employeeName": f"{r.FirstName} {r.LastName}", "department": r.Department, "startDate": r.StartDate, "status": r.Status, "progress": r.Progress} for r in cursor.fetchall()]
        return jsonify(onboarding)
    finally:
        if cursor: cursor.connection.close()

@app.route('/api/promotions', methods=['GET', 'POST'])
def handle_promotions():
    cursor = get_db_cursor()
    if not cursor: return jsonify({"message": "Database error"}), 500
    try:
        if request.method == 'POST':
            data = request.get_json()
            cursor.execute("SELECT Position FROM Users WHERE UserID = ?", (data['employeeId'],))
            old_pos = cursor.fetchone()[0]
            cursor.execute("INSERT INTO Promotions (UserID, OldPosition, NewPosition, PromotionDate) VALUES (?, ?, ?, ?)", (data['employeeId'], old_pos, data['newPosition'], data['promotionDate']))
            cursor.execute("UPDATE Users SET Position = ? WHERE UserID = ?", (data['newPosition'], data['employeeId']))
            cursor.connection.commit()
            return jsonify({"message": "Promotion initiated!"}), 201

        cursor.execute("SELECT u.FirstName, u.LastName, p.NewPosition, p.PromotionDate, p.Status FROM Promotions p JOIN Users u ON p.UserID = u.UserID")
        promotions = [{"employeeName": f"{r.FirstName} {r.LastName}", "newPosition": r.NewPosition, "promotionDate": r.PromotionDate, "status": r.Status} for r in cursor.fetchall()]
        return jsonify(promotions)
    finally:
        if cursor: cursor.connection.close()

@app.route('/api/succession-plans', methods=['GET', 'POST'])
def handle_succession_plans():
    cursor = get_db_cursor()
    if not cursor: return jsonify({"message": "Database error"}), 500
    try:
        if request.method == 'POST':
            data = request.get_json()
            cursor.execute("INSERT INTO SuccessionPlans (CriticalRole, SuccessorID, Readiness) VALUES (?, ?, ?)", (data['criticalRole'], data['successorId'], data['readiness']))
            cursor.connection.commit()
            return jsonify({"message": "Succession plan added!"}), 201
        
        cursor.execute("SELECT s.CriticalRole, u.FirstName, u.LastName, s.Readiness FROM SuccessionPlans s JOIN Users u ON s.SuccessorID = u.UserID")
        plans = [{"criticalRole": r.CriticalRole, "successorName": f"{r.FirstName} {r.LastName}", "readiness": r.Readiness} for r in cursor.fetchall()]
        return jsonify(plans)
    finally:
        if cursor: cursor.connection.close()
    
@app.route('/api/employees/<int:user_id>/documents', methods=['GET', 'POST'])
def handle_documents(user_id):
    cursor = get_db_cursor()
    if not cursor: return jsonify({"message": "Database error"}), 500
    try:
        if request.method == 'POST':
            if 'file' not in request.files: return jsonify({"message": "No file part"}), 400
            file = request.files['file']
            category = request.form.get('category', 'General')
            if file.filename == '': return jsonify({"message": "No selected file"}), 400
            if file:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                
                cursor.execute("INSERT INTO Documents (UserID, DocumentName, Category, FilePath) VALUES (?, ?, ?, ?)",(user_id, filename, category, filename))
                cursor.connection.commit()
                return jsonify({"message": "File uploaded successfully!"}), 201

        cursor.execute("SELECT DocumentID, DocumentName, Category, UploadDate FROM Documents WHERE UserID = ?", (user_id,))
        docs = [{"documentID": r.DocumentID, "documentName": r.DocumentName, "category": r.Category, "uploadDate": r.UploadDate} for r in cursor.fetchall()]
        return jsonify(docs)
    finally:
        if cursor: cursor.connection.close()

@app.route('/api/documents/<int:doc_id>', methods=['GET'])
def download_document(doc_id):
    cursor = get_db_cursor()
    if not cursor: return jsonify({"message": "Database error"}), 500
    try:
        cursor.execute("SELECT FilePath FROM Documents WHERE DocumentID = ?", (doc_id,))
        doc = cursor.fetchone()
        if doc and doc.FilePath:
            try:
                return send_from_directory(app.config['UPLOAD_FOLDER'], doc.FilePath, as_attachment=True)
            except FileNotFoundError:
                 return jsonify({"message": "File not found on server."}), 404
        return jsonify({"message": "Document record not found."}), 404
    finally:
        if cursor: cursor.connection.close()

if __name__ == '__main__':
    app.run(debug=True, port=5000)

