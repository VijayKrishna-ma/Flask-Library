from flask import Flask, render_template, request, redirect, session, url_for, flash
import db
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'very_secret_key_for_session_management'  # Change this key later

# ========== HOME ROUTES ==========

@app.route('/')
def home():
    return redirect(url_for('student_login'))

# ========== LOGIN ROUTES ==========

@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        roll_number = request.form['roll_number']
        student = db.execute_select("SELECT * FROM lib_users WHERE roll_number = :1", (roll_number,))
        if student:
            session['role'] = 'student'
            session['roll_number'] = roll_number
            return redirect(url_for('student_profile'))
        else:
            flash('Invalid Roll Number. Please try again.', 'error')
    return render_template('student_login.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['admin_username']
        password = request.form['admin_password']
        admin = db.execute_select("SELECT * FROM admin_user WHERE admin_username = :1 AND admin_password = :2", (username, password))
        if admin:
            session['role'] = 'admin'
            session['admin_username'] = username
            return redirect(url_for('admin_profile'))
        else:
            flash('Invalid Admin Credentials.', 'error')
    return render_template('admin_login.html')

# ========== STUDENT PROFILE ==========

@app.route('/student_profile')
def student_profile():
    if session.get('role') != 'student':
        return redirect(url_for('student_login'))
    
    roll_number = session['roll_number']
    student_info = db.execute_select("SELECT * FROM lib_users WHERE roll_number = :1", (roll_number,))
    loans = db.execute_select("SELECT * FROM lib_loan WHERE roll_number = :1", (roll_number,))
    return render_template('student_profile.html', student=student_info[0], loans=loans)

# ========== ADMIN PROFILE ==========

@app.route('/admin_profile', methods=['GET', 'POST'])
def admin_profile():
    if session.get('role') != 'admin':
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        roll_number = request.form['roll_number']
        book_ID = request.form['book_ID']
        start_date = datetime.now()
        end_date = start_date + timedelta(days=14)
        db.execute_query("INSERT INTO lib_loan (roll_number, book_ID, start_date, end_date, fine) VALUES (:1, :2, :3, :4, 0)", 
                         (roll_number, book_ID, start_date, end_date))

    loans = db.execute_select("""
        SELECT l.roll_number, l.book_ID, b.book_title, l.start_date, l.end_date, l.fine
        FROM lib_loan l
        JOIN lib_book b ON l.book_ID = b.book_ID
    """)
    return render_template('admin_profile.html', loans=loans)

# ========== STUDENT CATALOG ==========

@app.route('/student_catalog')
def student_catalog():
    books = db.execute_select("""
        SELECT book_title, book_author, book_category, book_edition, COUNT(book_ID) AS stock
        FROM lib_book
        GROUP BY book_title, book_author, book_category, book_edition
    """)
    return render_template('student_catalog.html', books=books)

# ========== ADMIN CATALOG ==========

@app.route('/admin_catalog', methods=['GET', 'POST'])
def admin_catalog():
    if session.get('role') != 'admin':
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        title = request.form['book_title']
        author = request.form['book_author']
        category = request.form['book_category']
        edition = request.form['book_edition']
        book_id = request.form['book_ID']
        db.execute_query("INSERT INTO lib_book (book_ID, book_title, book_author, book_category, book_edition) VALUES (:1, :2, :3, :4, :5)", 
                         (book_id, title, author, category, edition))
        
    books = db.execute_select("""
        SELECT book_title, book_author, book_category, book_edition, COUNT(book_ID) AS stock
        FROM lib_book
        GROUP BY book_title, book_author, book_category, book_edition
    """)
    return render_template('admin_catalog.html', books=books)

# ========== STATS PAGE ==========

@app.route('/stats')
def stats():
    book_counts = db.execute_select("""
        SELECT book_category, COUNT(*) as count
        FROM lib_book
        GROUP BY book_category
    """)
    return render_template('stats.html', book_counts=book_counts)

# ========== LOGOUT ==========

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# ========== FINE MANAGEMENT CRON JOB ==========

@app.before_request
def calculate_fines():
    loans = db.execute_select("SELECT roll_number, book_ID, end_date FROM lib_loan")
    if loans:
        for loan in loans:
            end_date = loan['END_DATE']
            today = datetime.now()
            fine = 0
            if today > end_date:
                days_overdue = (today - end_date).days
                if days_overdue > 14:
                    fine = 5
                elif days_overdue > 7:
                    fine = 1
                else:
                    fine = 0
            db.execute_query("UPDATE lib_loan SET fine = :1 WHERE roll_number = :2 AND book_ID = :3",
                             (fine, loan['ROLL_NUMBER'], loan['BOOK_ID']))

# ========== CONTACT / COMPLAINT PAGE ==========

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if 'roll_number' not in session:
        return redirect(url_for('student_login'))

    if request.method == 'POST':
        topic = request.form['topic']
        complaint = request.form['complaint']
        roll_number = session['roll_number']
        
        db.execute_query(
            "INSERT INTO text (texts, topic, roll_number) VALUES (:1, :2, :3)",  # corrected here
            (complaint, topic, roll_number)
        )
        
        flash('Complaint submitted successfully!', 'success')
        return redirect(url_for('contact'))
    
    return render_template('contact.html')


# ========== COMPLAINT RECEIVAL PAGE ==========

# ========== COMPLAINT RECEIVAL ROUTE ==========
@app.route('/recieval')
def recieval():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))

    query = '''
    SELECT t.roll_number, u.name, t.topic, t.texts
    FROM text t
    JOIN lib_users u ON t.roll_number = u.roll_number
    '''
    complaints = db.execute_select(query)

    complaint_list = []
    for complaint in complaints:
        complaint_dict = {
            'ROLL_NUMBER': complaint['ROLL_NUMBER'],
            'NAME': complaint['NAME'],
            'TOPIC': complaint['TOPIC'],
            'TEXT': str(complaint['TEXTS'])  # careful: use correct column names
        }
        complaint_list.append(complaint_dict)

    return render_template('recieval.html', complaints=complaint_list)



@app.route('/admin_stats')
def admin_stats():
    if session.get('role') != 'admin':
        return redirect(url_for('admin_login'))
    
    # Fetch fines
    fines = db.execute_select('''
        SELECT roll_number, SUM(fine) AS total_fine
        FROM lib_loan
        GROUP BY roll_number
    ''')
    
    # Fetch loans count
    loans = db.execute_select('''
        SELECT roll_number, COUNT(*) AS loan_count
        FROM lib_loan
        GROUP BY roll_number
    ''')

    # Fetch complaints count (assuming you have timestamps, otherwise simple count)
    complaints = db.execute_select('''
        SELECT roll_number, COUNT(*) AS complaint_count
        FROM text
        GROUP BY roll_number
    ''')

    return render_template('admin_stats.html', fines=fines, loans=loans, complaints=complaints)

# ========== RUNNING FLASK SERVER ==========

if __name__ == '__main__':
    app.run(debug=True)
