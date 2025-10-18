from flask import Flask, request, jsonify
import pyodbc

app = Flask(__name__)

# Step 1: Connect to SQL Server
conn_str = (
    "Driver={SQL Server};"
    "Server=RAKSHIT\SQLEXPRESS;"  # change if your SSMS server name is different
    "Database=HRFloDB;"
    "Trusted_Connection=yes;"
)
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

# Step 2: Simple route to fetch employees
@app.route('/employees', methods=['GET'])
def get_employees():
    cursor.execute("SELECT * FROM Employees")
    rows = cursor.fetchall()
    data = []
    for row in rows:
        data.append({
            "EmployeeID": row.EmployeeID,
            "FirstName": row.FirstName,
            "LastName": row.LastName,
            "Email": row.Email,
            "Position": row.Position
        })
    return jsonify(data)

# Step 3: Insert employee
@app.route('/add_employee', methods=['POST'])
def add_employee():
    data = request.get_json()
    cursor.execute("""
        INSERT INTO Employees (FirstName, LastName, Email, Position, Department, HireDate)
        VALUES (?, ?, ?, ?, ?, GETDATE())
    """, (data['FirstName'], data['LastName'], data['Email'], data['Position'], data['Department']))
    conn.commit()
    return jsonify({"message": "Employee added successfully!"})

if __name__ == '__main__':
    app.run(debug=True)
