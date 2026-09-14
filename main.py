import os
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'kelas_kuliah_rahasia_123'

# --- INISIALISASI DATABASE ---
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Tabel Users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nama TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    
    # Tabel Kas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tanggal TEXT NOT NULL,
            keterangan TEXT NOT NULL,
            jenis TEXT NOT NULL,
            jumlah INTEGER NOT NULL,
            user_id INTEGER
        )
    ''')
    
    # Tabel Absen
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS absen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tanggal TEXT NOT NULL,
            nama TEXT NOT NULL,
            status TEXT NOT NULL
        )
    ''')
    
    # Akun Default saat pertama kali aplikasi dinyalakan
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password, nama, role) VALUES ('admin', 'admin123', 'Admin Kelas', 'Admin')")
        cursor.execute("INSERT INTO users (username, password, nama, role) VALUES ('bendahara', '12345', 'Bendahara Kelas', 'Bendahara')")
        cursor.execute("INSERT INTO users (username, password, nama, role) VALUES ('mahasiswa', '12345', 'Budi Mahasiswa', 'Anggota')")
    
    conn.commit()
    conn.close()

init_db()

# --- DEKORATOR CEK LOGIN ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- ROUTES / HALAMAN ---

@app.route('/')
@login_required
def dashboard():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Hitung Saldo Kas Kelas
    cursor.execute("SELECT SUM(CASE WHEN jenis='Masuk' THEN jumlah ELSE -jumlah END) FROM kas")
    saldo = cursor.fetchone()[0] or 0
    
    conn.close()
    return render_template('dashboard.html', saldo=saldo)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['nama'] = user[3]
            session['role'] = user[4]
            return redirect(url_for('dashboard'))
        else:
            flash('Username atau password salah!')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- FITUR KAS KELAS ---
@app.route('/kas', methods=['GET', 'POST'])
@login_required
def kas():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    if request.method == 'POST':
        if session['role'] not in ['Admin', 'Bendahara']:
            flash('Akses ditolak! Hanya Admin/Bendahara yang bisa input Kas.')
            return redirect(url_for('kas'))
            
        tanggal = request.form['tanggal']
        keterangan = request.form['keterangan']
        jenis = request.form['jenis']
        jumlah = request.form['jumlah']
        
        cursor.execute("INSERT INTO kas (tanggal, keterangan, jenis, jumlah, user_id) VALUES (?, ?, ?, ?, ?)",
                       (tanggal, keterangan, jenis, jumlah, session['user_id']))
        conn.commit()
        flash('Transaksi Kas Berhasil Ditambahkan!')
    
    cursor.execute("SELECT * FROM kas ORDER BY id DESC")
    data_kas = cursor.fetchall()
    conn.close()
    return render_template('kas.html', data_kas=data_kas)

# --- FITUR ABSENSI ---
@app.route('/absen', methods=['GET', 'POST'])
@login_required
def absen():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    if request.method == 'POST':
        tanggal = request.form['tanggal']
        status = request.form['status']
        nama = session['nama']
        
        cursor.execute("INSERT INTO absen (tanggal, nama, status) VALUES (?, ?, ?)", (tanggal, nama, status))
        conn.commit()
        flash('Absensi Berhasil!')
        
    cursor.execute("SELECT * FROM absen ORDER BY id DESC")
    data_absen = cursor.fetchall()
    conn.close()
    return render_template('absen.html', data_absen=data_absen)

# --- FITUR KELOLA ANGGOTA (KHUSUS ADMIN) ---
@app.route('/anggota', methods=['GET', 'POST'])
@login_required
def anggota():
    if session['role'] != 'Admin':
        flash('Halaman ini khusus untuk Admin!')
        return redirect(url_for('dashboard'))
        
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        nama = request.form['nama']
        role = request.form['role']
        
        try:
            cursor.execute("INSERT INTO users (username, password, nama, role) VALUES (?, ?, ?, ?)",
                           (username, password, nama, role))
            conn.commit()
            flash('Anggota Berhasil Ditambahkan!')
        except:
            flash('Username sudah digunakan!')
            
    cursor.execute("SELECT id, username, nama, role FROM users")
    users = cursor.fetchall()
    conn.close()
    return render_template('anggota.html', users=users)

@app.route('/hapus_anggota/<int:id>')
@login_required
def hapus_anggota(id):
    if session['role'] == 'Admin':
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        flash('Anggota dihapus!')
    return redirect(url_for('anggota'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
