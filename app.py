from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = 'library_secret_key_2024_change_in_production'

DATABASE = 'library.db'

# ─────────────────────────────────────────────
#  DATABASE HELPERS
# ─────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                name     TEXT    NOT NULL,
                email    TEXT    UNIQUE NOT NULL,
                password TEXT    NOT NULL,
                role     TEXT    NOT NULL DEFAULT 'student',
                phone    TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS books (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT    NOT NULL,
                author      TEXT    NOT NULL,
                category    TEXT    NOT NULL,
                isbn        TEXT,
                publisher   TEXT,
                year        INTEGER,
                quantity    INTEGER NOT NULL DEFAULT 1,
                available   INTEGER NOT NULL DEFAULT 1,
                description TEXT,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS issued_books (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id     INTEGER NOT NULL,
                user_id     INTEGER NOT NULL,
                issue_date  DATETIME DEFAULT CURRENT_TIMESTAMP,
                due_date    DATETIME,
                return_date DATETIME,
                status      TEXT DEFAULT 'issued',
                issued_by   INTEGER,
                FOREIGN KEY (book_id) REFERENCES books(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS book_requests (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id     INTEGER NOT NULL,
                user_id     INTEGER NOT NULL,
                request_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                status      TEXT DEFAULT 'pending',
                FOREIGN KEY (book_id) REFERENCES books(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        ''')

        # Seed default users if empty
        cur = db.execute("SELECT COUNT(*) FROM users")
        if cur.fetchone()[0] == 0:
            db.execute("INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                       ('Admin User', 'admin@library.com',
                        generate_password_hash('admin123'), 'admin'))
            db.execute("INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                       ('Jane Librarian', 'librarian@library.com',
                        generate_password_hash('lib123'), 'librarian'))
            db.execute("INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                       ('John Student', 'student@library.com',
                        generate_password_hash('student123'), 'student'))

        # Seed sample books if empty
        cur = db.execute("SELECT COUNT(*) FROM books")
        if cur.fetchone()[0] == 0:
            sample_books = [
                ('The Great Gatsby', 'F. Scott Fitzgerald', 'Fiction', '9780743273565', 'Scribner', 1925, 5, 5, 'A story of the mysterious millionaire Jay Gatsby.'),
                ('To Kill a Mockingbird', 'Harper Lee', 'Fiction', '9780061935466', 'HarperCollins', 1960, 4, 4, 'A novel about racial injustice and childhood.'),
                ('Introduction to Algorithms', 'CLRS', 'Technology', '9780262033848', 'MIT Press', 2009, 3, 3, 'The definitive CS algorithms textbook.'),
                ('Clean Code', 'Robert C. Martin', 'Technology', '9780132350884', 'Prentice Hall', 2008, 6, 6, 'A handbook of agile software craftsmanship.'),
                ('Sapiens', 'Yuval Noah Harari', 'History', '9780062316097', 'Harper', 2011, 4, 4, 'A brief history of humankind.'),
                ('Atomic Habits', 'James Clear', 'Self-Help', '9780735211292', 'Avery', 2018, 5, 5, 'Build good habits and break bad ones.'),
                ('The Pragmatic Programmer', 'Hunt & Thomas', 'Technology', '9780135957059', 'Addison-Wesley', 2019, 3, 3, 'From journeyman to master.'),
                ('1984', 'George Orwell', 'Fiction', '9780451524935', 'Signet', 1949, 4, 4, 'A dystopian novel about totalitarianism.'),
                ('Thinking, Fast and Slow', 'Daniel Kahneman', 'Psychology', '9780374533557', 'FSG', 2011, 3, 3, 'Two systems that drive the way we think.'),
                ('Brief History of Time', 'Stephen Hawking', 'Science', '9780553380163', 'Bantam', 1988, 2, 2, 'From the big bang to black holes.'),
                ('The Alchemist', 'Paulo Coelho', 'Fiction', '9780062315007', 'HarperOne', 1988, 6, 6, 'A philosophical novel about following dreams.'),
                ('Deep Work', 'Cal Newport', 'Self-Help', '9781455586691', 'Grand Central', 2016, 4, 4, 'Rules for focused success in a distracted world.'),
            ]
            for b in sample_books:
                db.execute("INSERT INTO books (title,author,category,isbn,publisher,year,quantity,available,description) VALUES (?,?,?,?,?,?,?,?,?)", b)

        db.commit()

# ─────────────────────────────────────────────
#  AUTH DECORATORS
# ─────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if session.get('role') not in roles:
                flash('Access denied.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator

# ─────────────────────────────────────────────
#  AUTH ROUTES
# ─────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('auth/login.html')
        db   = get_db()
        user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        db.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['name']    = user['name']
            session['role']    = user['role']
            session['email']   = user['email']
            flash(f"Welcome back, {user['name']}!", 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name     = request.form.get('name', '').strip()
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        phone    = request.form.get('phone', '').strip()
        if not name or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('auth/register.html')
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('auth/register.html')
        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if existing:
            flash('Email already registered.', 'danger')
            db.close()
            return render_template('auth/register.html')
        db.execute("INSERT INTO users (name,email,password,role,phone) VALUES (?,?,?,?,?)",
                   (name, email, generate_password_hash(password), 'student', phone))
        db.commit()
        db.close()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('auth/register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

# ─────────────────────────────────────────────
#  DASHBOARD ROUTER
# ─────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    role = session.get('role')
    if role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif role == 'librarian':
        return redirect(url_for('librarian_dashboard'))
    else:
        return redirect(url_for('student_dashboard'))

# ─────────────────────────────────────────────
#  ADMIN ROUTES
# ─────────────────────────────────────────────

@app.route('/admin/dashboard')
@role_required('admin')
def admin_dashboard():
    db = get_db()
    stats = {
        'total_books':    db.execute("SELECT COUNT(*) FROM books").fetchone()[0],
        'total_users':    db.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0],
        'issued_books':   db.execute("SELECT COUNT(*) FROM issued_books WHERE status='issued'").fetchone()[0],
        'pending_req':    db.execute("SELECT COUNT(*) FROM book_requests WHERE status='pending'").fetchone()[0],
        'overdue':        db.execute("SELECT COUNT(*) FROM issued_books WHERE status='issued' AND due_date < ?",
                                     (datetime.now(),)).fetchone()[0],
        'total_librarians': db.execute("SELECT COUNT(*) FROM users WHERE role='librarian'").fetchone()[0],
    }
    recent_issues = db.execute("""
        SELECT ib.*, b.title, u.name as student_name
        FROM issued_books ib
        JOIN books b ON ib.book_id=b.id
        JOIN users u ON ib.user_id=u.id
        ORDER BY ib.issue_date DESC LIMIT 8
    """).fetchall()
    categories = db.execute("""
        SELECT category, COUNT(*) as cnt FROM books GROUP BY category ORDER BY cnt DESC LIMIT 6
    """).fetchall()
    db.close()
    now = datetime.now()
    return render_template('admin/dashboard.html', stats=stats,
                           recent_issues=recent_issues, categories=categories, now=now)

@app.route('/admin/books')
@role_required('admin')
def admin_books():
    search = request.args.get('q', '')
    cat    = request.args.get('cat', '')
    db     = get_db()
    query  = "SELECT * FROM books WHERE 1=1"
    params = []
    if search:
        query  += " AND (title LIKE ? OR author LIKE ? OR isbn LIKE ?)"
        params += [f'%{search}%', f'%{search}%', f'%{search}%']
    if cat:
        query  += " AND category=?"
        params.append(cat)
    query += " ORDER BY created_at DESC"
    books      = db.execute(query, params).fetchall()
    categories = db.execute("SELECT DISTINCT category FROM books ORDER BY category").fetchall()
    db.close()
    return render_template('admin/books.html', books=books,
                           categories=categories, search=search, selected_cat=cat)

@app.route('/admin/books/add', methods=['GET', 'POST'])
@role_required('admin')
def admin_add_book():
    if request.method == 'POST':
        title       = request.form['title'].strip()
        author      = request.form['author'].strip()
        category    = request.form['category'].strip()
        isbn        = request.form.get('isbn', '').strip()
        publisher   = request.form.get('publisher', '').strip()
        year        = request.form.get('year') or None
        quantity    = int(request.form.get('quantity', 1))
        description = request.form.get('description', '').strip()
        if not title or not author or not category:
            flash('Title, author, and category are required.', 'danger')
            return redirect(url_for('admin_add_book'))
        db = get_db()
        db.execute("""INSERT INTO books (title,author,category,isbn,publisher,year,quantity,available,description)
                      VALUES (?,?,?,?,?,?,?,?,?)""",
                   (title, author, category, isbn, publisher, year, quantity, quantity, description))
        db.commit()
        db.close()
        flash(f'Book "{title}" added successfully!', 'success')
        return redirect(url_for('admin_books'))
    return render_template('admin/book_form.html', book=None, action='Add')

@app.route('/admin/books/edit/<int:book_id>', methods=['GET', 'POST'])
@role_required('admin')
def admin_edit_book(book_id):
    db   = get_db()
    book = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
    if not book:
        flash('Book not found.', 'danger')
        return redirect(url_for('admin_books'))
    if request.method == 'POST':
        title       = request.form['title'].strip()
        author      = request.form['author'].strip()
        category    = request.form['category'].strip()
        isbn        = request.form.get('isbn', '').strip()
        publisher   = request.form.get('publisher', '').strip()
        year        = request.form.get('year') or None
        quantity    = int(request.form.get('quantity', 1))
        description = request.form.get('description', '').strip()
        # Recalculate available
        issued_count = db.execute(
            "SELECT COUNT(*) FROM issued_books WHERE book_id=? AND status='issued'",
            (book_id,)).fetchone()[0]
        available = max(0, quantity - issued_count)
        db.execute("""UPDATE books SET title=?,author=?,category=?,isbn=?,publisher=?,
                      year=?,quantity=?,available=?,description=? WHERE id=?""",
                   (title, author, category, isbn, publisher, year, quantity, available, description, book_id))
        db.commit()
        db.close()
        flash(f'Book "{title}" updated successfully!', 'success')
        return redirect(url_for('admin_books'))
    db.close()
    return render_template('admin/book_form.html', book=book, action='Edit')

@app.route('/admin/books/delete/<int:book_id>', methods=['POST'])
@role_required('admin')
def admin_delete_book(book_id):
    db = get_db()
    issued = db.execute(
        "SELECT COUNT(*) FROM issued_books WHERE book_id=? AND status='issued'",
        (book_id,)).fetchone()[0]
    if issued > 0:
        flash('Cannot delete: book has active issues.', 'danger')
    else:
        db.execute("DELETE FROM books WHERE id=?", (book_id,))
        db.commit()
        flash('Book deleted successfully.', 'success')
    db.close()
    return redirect(url_for('admin_books'))

@app.route('/admin/users')
@role_required('admin')
def admin_users():
    role   = request.args.get('role', '')
    search = request.args.get('q', '')
    db     = get_db()
    query  = "SELECT * FROM users WHERE 1=1"
    params = []
    if role:
        query += " AND role=?"
        params.append(role)
    if search:
        query  += " AND (name LIKE ? OR email LIKE ?)"
        params += [f'%{search}%', f'%{search}%']
    query += " ORDER BY created_at DESC"
    users = db.execute(query, params).fetchall()
    db.close()
    return render_template('admin/users.html', users=users,
                           selected_role=role, search=search)

@app.route('/admin/users/add', methods=['GET', 'POST'])
@role_required('admin')
def admin_add_user():
    if request.method == 'POST':
        name     = request.form['name'].strip()
        email    = request.form['email'].strip()
        password = request.form['password']
        role     = request.form['role']
        phone    = request.form.get('phone', '').strip()
        if not name or not email or not password or not role:
            flash('All required fields must be filled.', 'danger')
            return redirect(url_for('admin_add_user'))
        db = get_db()
        if db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone():
            flash('Email already exists.', 'danger')
            db.close()
            return redirect(url_for('admin_add_user'))
        db.execute("INSERT INTO users (name,email,password,role,phone) VALUES (?,?,?,?,?)",
                   (name, email, generate_password_hash(password), role, phone))
        db.commit()
        db.close()
        flash(f'User "{name}" created successfully!', 'success')
        return redirect(url_for('admin_users'))
    return render_template('admin/user_form.html', user=None, action='Add')

@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
@role_required('admin')
def admin_edit_user(user_id):
    db   = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin_users'))
    if request.method == 'POST':
        name  = request.form['name'].strip()
        email = request.form['email'].strip()
        role  = request.form['role']
        phone = request.form.get('phone', '').strip()
        pw    = request.form.get('password', '').strip()
        if pw:
            db.execute("UPDATE users SET name=?,email=?,role=?,phone=?,password=? WHERE id=?",
                       (name, email, role, phone, generate_password_hash(pw), user_id))
        else:
            db.execute("UPDATE users SET name=?,email=?,role=?,phone=? WHERE id=?",
                       (name, email, role, phone, user_id))
        db.commit()
        db.close()
        flash(f'User "{name}" updated!', 'success')
        return redirect(url_for('admin_users'))
    db.close()
    return render_template('admin/user_form.html', user=user, action='Edit')

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@role_required('admin')
def admin_delete_user(user_id):
    if user_id == session['user_id']:
        flash("You can't delete your own account.", 'danger')
        return redirect(url_for('admin_users'))
    db = get_db()
    db.execute("DELETE FROM users WHERE id=?", (user_id,))
    db.commit()
    db.close()
    flash('User deleted successfully.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/reports')
@role_required('admin')
def admin_reports():
    db = get_db()
    issued_books = db.execute("""
        SELECT ib.*, b.title, b.author, b.category,
               u.name as student_name, u.email as student_email
        FROM issued_books ib
        JOIN books b ON ib.book_id=b.id
        JOIN users u ON ib.user_id=u.id
        ORDER BY ib.issue_date DESC
    """).fetchall()
    overdue = db.execute("""
        SELECT ib.*, b.title, u.name as student_name, u.email as student_email
        FROM issued_books ib
        JOIN books b ON ib.book_id=b.id
        JOIN users u ON ib.user_id=u.id
        WHERE ib.status='issued' AND ib.due_date < ?
        ORDER BY ib.due_date ASC
    """, (datetime.now(),)).fetchall()
    top_books = db.execute("""
        SELECT b.title, b.author, COUNT(ib.id) as issue_count
        FROM issued_books ib JOIN books b ON ib.book_id=b.id
        GROUP BY b.id ORDER BY issue_count DESC LIMIT 10
    """).fetchall()
    requests = db.execute("""
        SELECT br.*, b.title, u.name as student_name
        FROM book_requests br
        JOIN books b ON br.book_id=b.id
        JOIN users u ON br.user_id=u.id
        ORDER BY br.request_date DESC
    """).fetchall()
    db.close()
    now = datetime.now()
    return render_template('admin/reports.html', issued_books=issued_books,
                           overdue=overdue, top_books=top_books,
                           requests=requests, now=now)

# ─────────────────────────────────────────────
#  LIBRARIAN ROUTES
# ─────────────────────────────────────────────

@app.route('/librarian/dashboard')
@role_required('librarian')
def librarian_dashboard():
    db = get_db()
    stats = {
        'total_books':  db.execute("SELECT COUNT(*) FROM books").fetchone()[0],
        'issued_today': db.execute(
            "SELECT COUNT(*) FROM issued_books WHERE DATE(issue_date)=DATE('now')").fetchone()[0],
        'returned_today': db.execute(
            "SELECT COUNT(*) FROM issued_books WHERE DATE(return_date)=DATE('now')").fetchone()[0],
        'overdue': db.execute(
            "SELECT COUNT(*) FROM issued_books WHERE status='issued' AND due_date < ?",
            (datetime.now(),)).fetchone()[0],
        'pending_req': db.execute(
            "SELECT COUNT(*) FROM book_requests WHERE status='pending'").fetchone()[0],
        'available_books': db.execute(
            "SELECT COUNT(*) FROM books WHERE available > 0").fetchone()[0],
    }
    recent = db.execute("""
        SELECT ib.*, b.title, u.name as student_name
        FROM issued_books ib
        JOIN books b ON ib.book_id=b.id
        JOIN users u ON ib.user_id=u.id
        ORDER BY ib.issue_date DESC LIMIT 10
    """).fetchall()
    pending_requests = db.execute("""
        SELECT br.*, b.title, u.name as student_name, b.available
        FROM book_requests br
        JOIN books b ON br.book_id=b.id
        JOIN users u ON br.user_id=u.id
        WHERE br.status='pending'
        ORDER BY br.request_date DESC
    """).fetchall()
    db.close()
    now = datetime.now()
    return render_template('librarian/dashboard.html', stats=stats,
                           recent=recent, pending_requests=pending_requests, now=now)

@app.route('/librarian/issue', methods=['GET', 'POST'])
@role_required('librarian')
def librarian_issue():
    db = get_db()
    if request.method == 'POST':
        book_id  = int(request.form['book_id'])
        user_id  = int(request.form['user_id'])
        days     = int(request.form.get('days', 14))
        due_date = datetime.now() + timedelta(days=days)
        book = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        if not book or book['available'] <= 0:
            flash('Book not available for issue.', 'danger')
        else:
            already = db.execute(
                "SELECT id FROM issued_books WHERE book_id=? AND user_id=? AND status='issued'",
                (book_id, user_id)).fetchone()
            if already:
                flash('Student already has this book issued.', 'warning')
            else:
                db.execute("""INSERT INTO issued_books (book_id,user_id,due_date,issued_by,status)
                              VALUES (?,?,?,?,'issued')""",
                           (book_id, user_id, due_date, session['user_id']))
                db.execute("UPDATE books SET available=available-1 WHERE id=?", (book_id,))
                # Remove pending request if exists
                db.execute("UPDATE book_requests SET status='approved' WHERE book_id=? AND user_id=? AND status='pending'",
                           (book_id, user_id))
                db.commit()
                flash('Book issued successfully!', 'success')
        db.close()
        return redirect(url_for('librarian_issue'))
    books    = db.execute("SELECT * FROM books WHERE available > 0 ORDER BY title").fetchall()
    students = db.execute("SELECT * FROM users WHERE role='student' ORDER BY name").fetchall()
    db.close()
    return render_template('librarian/issue_book.html', books=books, students=students)

@app.route('/librarian/return', methods=['GET', 'POST'])
@role_required('librarian')
def librarian_return():
    db = get_db()
    if request.method == 'POST':
        issue_id = int(request.form['issue_id'])
        record   = db.execute("SELECT * FROM issued_books WHERE id=?", (issue_id,)).fetchone()
        if not record:
            flash('Record not found.', 'danger')
        elif record['status'] == 'returned':
            flash('Book already returned.', 'warning')
        else:
            db.execute("UPDATE issued_books SET status='returned', return_date=? WHERE id=?",
                       (datetime.now(), issue_id))
            db.execute("UPDATE books SET available=available+1 WHERE id=?", (record['book_id'],))
            db.commit()
            flash('Book returned successfully!', 'success')
        db.close()
        return redirect(url_for('librarian_return'))
    active = db.execute("""
        SELECT ib.*, b.title, b.author, u.name as student_name, u.email as student_email
        FROM issued_books ib
        JOIN books b ON ib.book_id=b.id
        JOIN users u ON ib.user_id=u.id
        WHERE ib.status='issued'
        ORDER BY ib.due_date ASC
    """).fetchall()
    db.close()
    now = datetime.now()
    return render_template('librarian/return_book.html', active=active, now=now)

@app.route('/librarian/approve_request/<int:req_id>', methods=['POST'])
@role_required('librarian')
def approve_request(req_id):
    db  = get_db()
    req = db.execute("SELECT * FROM book_requests WHERE id=?", (req_id,)).fetchone()
    if req:
        book = db.execute("SELECT * FROM books WHERE id=?", (req['book_id'],)).fetchone()
        if book and book['available'] > 0:
            due_date = datetime.now() + timedelta(days=14)
            db.execute("""INSERT INTO issued_books (book_id,user_id,due_date,issued_by,status)
                          VALUES (?,?,?,?,'issued')""",
                       (req['book_id'], req['user_id'], due_date, session['user_id']))
            db.execute("UPDATE books SET available=available-1 WHERE id=?", (req['book_id'],))
            db.execute("UPDATE book_requests SET status='approved' WHERE id=?", (req_id,))
            db.commit()
            flash('Request approved and book issued!', 'success')
        else:
            flash('Book not available.', 'danger')
    db.close()
    return redirect(url_for('librarian_dashboard'))

@app.route('/librarian/reject_request/<int:req_id>', methods=['POST'])
@role_required('librarian')
def reject_request(req_id):
    db = get_db()
    db.execute("UPDATE book_requests SET status='rejected' WHERE id=?", (req_id,))
    db.commit()
    db.close()
    flash('Request rejected.', 'info')
    return redirect(url_for('librarian_dashboard'))

@app.route('/librarian/update_stock/<int:book_id>', methods=['POST'])
@role_required('librarian')
def update_stock(book_id):
    db       = get_db()
    quantity = int(request.form['quantity'])
    issued   = db.execute(
        "SELECT COUNT(*) FROM issued_books WHERE book_id=? AND status='issued'",
        (book_id,)).fetchone()[0]
    available = max(0, quantity - issued)
    db.execute("UPDATE books SET quantity=?, available=? WHERE id=?",
               (quantity, available, book_id))
    db.commit()
    db.close()
    flash('Stock updated successfully.', 'success')
    return redirect(url_for('librarian_books'))

@app.route('/librarian/books')
@role_required('librarian')
def librarian_books():
    search = request.args.get('q', '')
    db     = get_db()
    if search:
        books = db.execute(
            "SELECT * FROM books WHERE title LIKE ? OR author LIKE ? ORDER BY title",
            (f'%{search}%', f'%{search}%')).fetchall()
    else:
        books = db.execute("SELECT * FROM books ORDER BY title").fetchall()
    db.close()
    return render_template('librarian/books.html', books=books, search=search)

# ─────────────────────────────────────────────
#  STUDENT ROUTES
# ─────────────────────────────────────────────

@app.route('/student/dashboard')
@role_required('student')
def student_dashboard():
    db  = get_db()
    uid = session['user_id']
    stats = {
        'issued':   db.execute(
            "SELECT COUNT(*) FROM issued_books WHERE user_id=? AND status='issued'",
            (uid,)).fetchone()[0],
        'returned': db.execute(
            "SELECT COUNT(*) FROM issued_books WHERE user_id=? AND status='returned'",
            (uid,)).fetchone()[0],
        'pending':  db.execute(
            "SELECT COUNT(*) FROM book_requests WHERE user_id=? AND status='pending'",
            (uid,)).fetchone()[0],
        'overdue':  db.execute(
            "SELECT COUNT(*) FROM issued_books WHERE user_id=? AND status='issued' AND due_date < ?",
            (uid, datetime.now())).fetchone()[0],
    }
    my_books = db.execute("""
        SELECT ib.*, b.title, b.author, b.category
        FROM issued_books ib JOIN books b ON ib.book_id=b.id
        WHERE ib.user_id=? AND ib.status='issued'
        ORDER BY ib.due_date ASC
    """, (uid,)).fetchall()
    recent_books = db.execute(
        "SELECT * FROM books ORDER BY created_at DESC LIMIT 6").fetchall()
    db.close()
    now = datetime.now()
    return render_template('student/dashboard.html', stats=stats,
                           my_books=my_books, recent_books=recent_books, now=now)

@app.route('/student/search')
@role_required('student')
def student_search():
    search = request.args.get('q', '')
    cat    = request.args.get('cat', '')
    db     = get_db()
    query  = "SELECT * FROM books WHERE 1=1"
    params = []
    if search:
        query  += " AND (title LIKE ? OR author LIKE ? OR category LIKE ?)"
        params += [f'%{search}%', f'%{search}%', f'%{search}%']
    if cat:
        query += " AND category=?"
        params.append(cat)
    query += " ORDER BY title"
    books      = db.execute(query, params).fetchall()
    categories = db.execute("SELECT DISTINCT category FROM books ORDER BY category").fetchall()
    # Already requested/issued books for this user
    uid      = session['user_id']
    issued   = [r['book_id'] for r in db.execute(
        "SELECT book_id FROM issued_books WHERE user_id=? AND status='issued'", (uid,)).fetchall()]
    requests = [r['book_id'] for r in db.execute(
        "SELECT book_id FROM book_requests WHERE user_id=? AND status='pending'", (uid,)).fetchall()]
    db.close()
    return render_template('student/search.html', books=books, categories=categories,
                           search=search, selected_cat=cat, issued=issued, requests=requests)

@app.route('/student/request/<int:book_id>', methods=['POST'])
@role_required('student')
def student_request(book_id):
    uid = session['user_id']
    db  = get_db()
    # Check already issued
    already_issued = db.execute(
        "SELECT id FROM issued_books WHERE book_id=? AND user_id=? AND status='issued'",
        (book_id, uid)).fetchone()
    already_requested = db.execute(
        "SELECT id FROM book_requests WHERE book_id=? AND user_id=? AND status='pending'",
        (book_id, uid)).fetchone()
    if already_issued:
        flash('You already have this book issued.', 'warning')
    elif already_requested:
        flash('You already have a pending request for this book.', 'warning')
    else:
        db.execute("INSERT INTO book_requests (book_id, user_id) VALUES (?,?)", (book_id, uid))
        db.commit()
        flash('Book request submitted successfully!', 'success')
    db.close()
    return redirect(url_for('student_search', q=request.args.get('q', '')))

@app.route('/student/my_books')
@role_required('student')
def student_my_books():
    uid = session['user_id']
    db  = get_db()
    issued = db.execute("""
        SELECT ib.*, b.title, b.author, b.category
        FROM issued_books ib JOIN books b ON ib.book_id=b.id
        WHERE ib.user_id=? ORDER BY ib.issue_date DESC
    """, (uid,)).fetchall()
    requests = db.execute("""
        SELECT br.*, b.title, b.author
        FROM book_requests br JOIN books b ON br.book_id=b.id
        WHERE br.user_id=? ORDER BY br.request_date DESC
    """, (uid,)).fetchall()
    db.close()
    now = datetime.now()
    return render_template('student/my_books.html', issued=issued,
                           requests=requests, now=now)

# ─────────────────────────────────────────────
#  API ENDPOINTS (for AJAX search)
# ─────────────────────────────────────────────

@app.route('/api/books/search')
@login_required
def api_books_search():
    q  = request.args.get('q', '')
    db = get_db()
    books = db.execute(
        "SELECT id, title, author FROM books WHERE (title LIKE ? OR author LIKE ?) AND available>0 LIMIT 10",
        (f'%{q}%', f'%{q}%')).fetchall()
    db.close()
    return jsonify([dict(b) for b in books])

@app.route('/api/students/search')
@login_required
def api_students_search():
    q  = request.args.get('q', '')
    db = get_db()
    students = db.execute(
        "SELECT id, name, email FROM users WHERE role='student' AND (name LIKE ? OR email LIKE ?) LIMIT 10",
        (f'%{q}%', f'%{q}%')).fetchall()
    db.close()
    return jsonify([dict(s) for s in students])

# ─────────────────────────────────────────────
#  RUN
# ─────────────────────────────────────────────

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db()
    else:
        init_db()

    app.run(host='0.0.0.0', port=5000, debug=True)