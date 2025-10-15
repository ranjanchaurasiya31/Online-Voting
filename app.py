from flask import Flask, render_template, request, flash, redirect, url_for, session, jsonify
import sqlite3

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Database setup
def init_db():
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS elections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'ongoing'
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                election_id INTEGER,
                FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                election_id INTEGER,
                candidate_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (election_id) REFERENCES elections(id),
                FOREIGN KEY (candidate_id) REFERENCES candidates(id)
            )
        """)
        conn.commit()

init_db()

# Home Page
@app.route('/')
def index():
    return render_template('index.html')

# Live votes
@app.route('/get_live_vote_count')
def get_live_vote_count():
    election_id = request.args.get('election_id')

    if not election_id:
        return jsonify({"error": "Election ID is required"}), 400

    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.id, c.name, COUNT(v.id) 
            FROM candidates c 
            LEFT JOIN votes v ON c.id = v.candidate_id 
            WHERE c.election_id = ? 
            GROUP BY c.id, c.name
        """, (election_id,))
        results = cursor.fetchall()

    # Convert to JSON
    vote_data = [{"candidate_id": row[0], "name": row[1], "votes": row[2]} for row in results]
    return jsonify(vote_data)

# View result
@app.route("/view_results")
def view_results():
    import sqlite3
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Fetch all vote counts for each candidate in each election
    cursor.execute("""
        SELECT elections.name, candidates.name, COUNT(votes.candidate_id) as vote_count
        FROM elections
        JOIN candidates ON elections.id = candidates.election_id
        LEFT JOIN votes ON candidates.id = votes.candidate_id
        GROUP BY elections.id, candidates.id
        ORDER BY elections.id, vote_count DESC
    """)
    results = cursor.fetchall()

    conn.close()

    # Organize winners: first candidate in each election (because sorted DESC)
    election_winners = {}
    election_names_set = set()

    for election, candidate, vote_count in results:
        election_names_set.add(election)
        if election not in election_winners:
            election_winners[election] = (candidate, vote_count)

    # Convert to list for dropdown
    election_names = sorted(list(election_names_set))

    return render_template(
        "view_results.html",
        results=results,
        election_winners=election_winners,
        election_names=election_names
    )

# Election Chart
@app.route("/election/<election_name>")
def view_election_chart(election_name):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Fetch vote count for all candidates in the selected election
    cursor.execute("""
        SELECT candidates.name, COUNT(votes.candidate_id) as vote_count
        FROM elections
        JOIN candidates ON elections.id = candidates.election_id
        LEFT JOIN votes ON candidates.id = votes.candidate_id
        WHERE elections.name = ?
        GROUP BY candidates.id
    """, (election_name,))
    
    data = cursor.fetchall()

    # Get all election names for the dropdown
    cursor.execute("SELECT name FROM elections")
    election_names = [row[0] for row in cursor.fetchall()]

    conn.close()

    labels = [row[0] for row in data]
    votes = [row[1] for row in data]

    return render_template("election_chart.html", election_name=election_name,
                            labels=labels, votes=votes, election_names=election_names)


# User Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()

            # Check if user already exists
            cursor.execute("SELECT * FROM users WHERE username=?", (username,))
            existing_user = cursor.fetchone()
            if existing_user:
                flash("Username already exists! Try another.", "danger")
            else:
                cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
                conn.commit()
                flash("Registration successful! You can now log in.", "success")
                return redirect(url_for('login'))

    return render_template('register.html')

# User Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
            user = cursor.fetchone()
            if user:
                session['user_id'] = user[0]
                return redirect(url_for('vote'))
            else:
                flash("Invalid login credentials!", "danger")

    return render_template('login.html')

# User dashboard
@app.route('/user_dashboard')
def user_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('user_login'))

    user_id = session['user_id']

    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()

        # Fetch available elections
        cursor.execute("SELECT id, name FROM elections")
        elections = cursor.fetchall()

        # Fetch candidates for each election
        cursor.execute("SELECT candidates.id, candidates.name, candidates.election_id FROM candidates")
        candidates = cursor.fetchall()

        # Fetch elections the user has already voted in
        cursor.execute("SELECT election_id FROM votes WHERE user_id=?", (user_id,))
        voted_elections = [row[0] for row in cursor.fetchall()]

    return render_template('user_dashboard.html', elections=elections, candidates=candidates, voted_elections=voted_elections)

# Submit vote
@app.route('/submit_vote', methods=['POST'])
def submit_vote():
    data = request.json
    election_id = data.get('election_id')
    candidate_id = data.get('candidate_id')
    user_id = session.get('user_id')

    if not election_id or not candidate_id or not user_id:
        return jsonify({"success": False, "message": "Invalid vote request."})

    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()

        # Check if the user has already voted in this election
        cursor.execute("SELECT * FROM votes WHERE user_id=? AND election_id=?", (user_id, election_id))
        if cursor.fetchone():
            return jsonify({"success": False, "message": "You have already voted in this election."})

        # Cast the vote
        cursor.execute("INSERT INTO votes (user_id, election_id, candidate_id) VALUES (?, ?, ?)", (user_id, election_id, candidate_id))
        conn.commit()

    return jsonify({"success": True})

# Thank you
@app.route('/thank_you')
def thank_you():
    return render_template('thank_you.html')

# Admin Login
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM admin WHERE username=? AND password=?", (username, password))
            admin = cursor.fetchone()
            if admin:
                session['admin_id'] = admin[0]
                return redirect(url_for('admin_dashboard'))
            else:
                flash("Invalid admin credentials!", "danger")

    return render_template('admin_login.html')

# Manage Users (Admin)
@app.route('/manage_users')
def manage_users():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username FROM users")
        users = cursor.fetchall()

    return render_template('manage_users.html', users=users)

# Remove User (Admin)
@app.route('/remove_user', methods=['POST'])
def remove_user():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    user_id = request.form.get('user_id')

    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.commit()

    flash("User removed successfully!", "success")
    return redirect(url_for('manage_users'))

# Admin Dashboard
@app.route('/admin_dashboard')
def admin_dashboard():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Fetch all elections
    cursor.execute("SELECT id, name FROM elections")
    elections = cursor.fetchall()
    print("DEBUG: Elections fetched ->", elections)  # Check if elections exist

    # Fetch all candidates with election name and vote count
    cursor.execute("""
        SELECT candidates.id, candidates.name, elections.name, 
               COALESCE((SELECT COUNT(*) FROM votes WHERE votes.candidate_id = candidates.id), 0) 
        FROM candidates
        JOIN elections ON candidates.election_id = elections.id
    """)
    candidates = cursor.fetchall()
    print("DEBUG: Candidates fetched ->", candidates)  # Debugging candidates list

    conn.close()

    return render_template('admin_dashboard.html', elections=elections, candidates=candidates)

# Admin - Manage Elections
@app.route('/manage_elections', methods=['GET', 'POST'])
def manage_elections():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        if request.method == 'POST':
            name = request.form['name']
            cursor.execute("INSERT INTO elections (name) VALUES (?)", (name,))
            conn.commit()
        cursor.execute("SELECT * FROM elections")
        elections = cursor.fetchall()
    
    return render_template('manage_elections.html', elections=elections)

# Remove election
@app.route('/remove_election', methods=['POST'])
def remove_election():
    election_id = request.form.get('election_id')

    if election_id:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        # Check if the election exists
        cursor.execute("SELECT * FROM elections WHERE id = ?", (election_id,))
        election = cursor.fetchone()
        if election:
            print(f"DEBUG: Removing election with ID {election_id}")  # Debugging

            # Remove candidates linked to the election
            cursor.execute("DELETE FROM candidates WHERE election_id = ?", (election_id,))
            # Remove the election
            cursor.execute("DELETE FROM elections WHERE id = ?", (election_id,))

            conn.commit()
        else:
            print(f"DEBUG: Election ID {election_id} not found")  # Debugging

        conn.close()

    return redirect(url_for('admin_dashboard'))

# Admin - Manage Candidates
@app.route('/manage_candidates', methods=['GET', 'POST'])
def manage_candidates():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        
        # Add Candidate
        if request.method == 'POST' and 'name' in request.form:
            name = request.form['name']
            election_id = request.form['election_id']
            
            # Check if election exists
            cursor.execute("SELECT id FROM elections WHERE id=?", (election_id,))
            election = cursor.fetchone()
            if election:
                cursor.execute("INSERT INTO candidates (name, election_id) VALUES (?, ?)", (name, election_id))
                conn.commit()
        
        # Fetch Elections
        cursor.execute("SELECT * FROM elections")
        elections = cursor.fetchall()
        
        # Fetch Candidates
        cursor.execute("""
            SELECT candidates.id, candidates.name, elections.name 
            FROM candidates 
            JOIN elections ON candidates.election_id = elections.id
        """)
        candidates = cursor.fetchall()
    
    return render_template('manage_candidates.html', elections=elections, candidates=candidates)

#creating election
@app.route('/create_election', methods=['GET', 'POST'])
def create_election():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        election_name = request.form['name']
        start_time = request.form['start_time']
        end_time = request.form['end_time']

        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO elections (name, start_time, end_time) 
                VALUES (?, ?, ?)
            """, (election_name, start_time, end_time))
            conn.commit()

        return redirect(url_for('manage_candidates'))
    
    return render_template('create_election.html')


#Remove candidates
@app.route('/remove_candidate', methods=['POST'])
def remove_candidate():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    candidate_id = request.form.get('candidate_id')
    
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        
        # Check if candidate exists before deleting
        cursor.execute("SELECT id FROM candidates WHERE id=?", (candidate_id,))
        candidate = cursor.fetchone()
        
        if candidate:
            cursor.execute("DELETE FROM candidates WHERE id=?", (candidate_id,))
            conn.commit()
    
    return redirect(url_for('manage_candidates'))

# API to Get Candidates for a Selected Election
@app.route('/get_candidates')
def get_candidates():
    election_id = request.args.get('election_id')
    
    if not election_id:
        return jsonify([])  # Return empty if no election is selected
    
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM candidates WHERE election_id=?", (election_id,))
        candidates = cursor.fetchall()
    
    return jsonify([{"id": c[0], "name": c[1]} for c in candidates])

# User - Vote
@app.route('/vote', methods=['GET', 'POST'])
def vote():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()

        # Fetch available elections
        cursor.execute("SELECT id, name FROM elections WHERE status='ongoing'")
        elections = cursor.fetchall()

        # Fetch candidates (Initially empty, will be fetched via AJAX)
        cursor.execute("SELECT id, name, election_id FROM candidates")
        candidates = cursor.fetchall()

    return render_template('vote.html', elections=elections, candidates=candidates)

# Vote Success Page
@app.route('/vote_success')
def vote_success():
    return render_template('vote_success.html')

# **Logout**
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
