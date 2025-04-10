from flask import Flask, render_template, request, jsonify, send_file
import sqlite3
from io import StringIO, BytesIO
import csv

app = Flask(__name__)

# Database initialization
def init_db():
    conn = sqlite3.connect('library.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS books
                 (book_id TEXT PRIMARY KEY, 
                  book_name TEXT, 
                  author_name TEXT, 
                  book_price REAL, 
                  book_qty INTEGER)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS issued_books
                 (book_id TEXT,
                  student_id TEXT,
                  return_date TEXT,
                  FOREIGN KEY (book_id) REFERENCES books (book_id))''')
    conn.commit()
    conn.close()

@app.route('/')
def home():
    conn = sqlite3.connect('library.db')
    c = conn.cursor()
    c.execute('SELECT * FROM books')
    books = c.fetchall()
    c.execute('SELECT * FROM issued_books')
    issued_books = c.fetchall()
    conn.close()
    return render_template('index.html', books=books, issued_books=issued_books)

@app.route('/add_book', methods=['POST'])
def add_book():
    data = request.get_json()
    try:
        conn = sqlite3.connect('library.db')
        c = conn.cursor()
        c.execute('INSERT INTO books VALUES (?, ?, ?, ?, ?)',
                 (data['bookId'], data['bookName'], data['authorName'], 
                  float(data['bookPrice']), int(data['bookQty'])))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Book added successfully!"})
    except sqlite3.IntegrityError:
        return jsonify({"status": "error", "message": "Book ID already exists!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/delete_book', methods=['POST'])
def delete_book():
    data = request.get_json()
    conn = sqlite3.connect('library.db')
    c = conn.cursor()
    c.execute('DELETE FROM books WHERE book_id = ?', (data['bookId'],))
    if c.rowcount > 0:
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Book deleted successfully!"})
    conn.close()
    return jsonify({"status": "error", "message": "Book not found!"})

@app.route('/issue_book', methods=['POST'])
def issue_book():
    data = request.get_json()
    conn = sqlite3.connect('library.db')
    c = conn.cursor()
    
    # Check if book exists and has available quantity
    c.execute('SELECT book_qty FROM books WHERE book_id = ?', (data['bookId'],))
    result = c.fetchone()
    
    if result and result[0] > 0:
        # Reduce quantity by 1
        c.execute('UPDATE books SET book_qty = book_qty - 1 WHERE book_id = ?', 
                 (data['bookId'],))
        # Add to issued books
        c.execute('INSERT INTO issued_books VALUES (?, ?, ?)',
                 (data['bookId'], data['studentId'], data['returnDate']))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Book issued successfully!"})
    
    conn.close()
    return jsonify({"status": "error", "message": "Book not available!"})

@app.route('/return_book', methods=['POST'])
def return_book():
    data = request.get_json()
    conn = sqlite3.connect('library.db')
    c = conn.cursor()
    
    # Check if book is issued
    c.execute('DELETE FROM issued_books WHERE book_id = ? AND student_id = ?', 
             (data['bookId'], data['studentId']))
    
    if c.rowcount > 0:
        # Increase book quantity by 1
        c.execute('UPDATE books SET book_qty = book_qty + 1 WHERE book_id = ?', 
                 (data['bookId'],))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Book returned successfully!"})
    
    conn.close()
    return jsonify({"status": "error", "message": "Book was not issued to this student!"})

@app.route('/download_books')
def download_books():
    conn = sqlite3.connect('library.db')
    c = conn.cursor()
    c.execute('SELECT * FROM books')
    books = c.fetchall()
    conn.close()
    
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Book ID', 'Book Name', 'Author Name', 'Price', 'Quantity'])
    writer.writerows(books)
    
    output = si.getvalue()
    bio = BytesIO()
    bio.write(output.encode('utf-8'))
    bio.seek(0)
    
    return send_file(
        bio,
        mimetype='text/csv',
        as_attachment=True,
        download_name='books.csv'
    )

@app.route('/view_issued_books')
def view_issued_books():
    conn = sqlite3.connect('library.db')
    c = conn.cursor()
    # Get issued books with book names
    c.execute('''
        SELECT i.book_id, b.book_name, i.student_id, i.return_date, b.book_qty 
        FROM issued_books i 
        LEFT JOIN books b ON i.book_id = b.book_id
    ''')
    issued_books = c.fetchall()
    
    # Get all books with their quantities
    c.execute('SELECT book_id, book_name, book_qty FROM books')
    available_books = c.fetchall()
    
    conn.close()
    return render_template('issued_books.html', 
                         issued_books=issued_books, 
                         available_books=available_books)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)