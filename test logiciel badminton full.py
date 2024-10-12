import sys
import sqlite3
import csv
import random
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QLabel, QLineEdit,
    QVBoxLayout, QHBoxLayout, QMessageBox, QTableWidget, QTableWidgetItem,
    QComboBox, QFileDialog, QDialog, QListWidget, QListWidgetItem, QFormLayout,
    QWidget, QMenu, QTextEdit, QAction, QAbstractItemView
)
from PyQt5.QtCore import Qt

# Constants
DATABASE = 'badminton_app.db'
MAX_FIELDS = 4  # Number of badminton fields

# Initialize the database
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Create players table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            elo_rating REAL DEFAULT 1500,
            matches_played INTEGER DEFAULT 0,
            skill_level TEXT,
            availability TEXT
        )
    ''')
    
    # Create sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            match_type TEXT,
            date TEXT
        )
    ''')
    
    # Create matches table with session_id
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            session_id INTEGER,
            player_a_id INTEGER,
            player_b_id INTEGER,
            score_a INTEGER,
            score_b INTEGER,
            winner_id INTEGER,
            match_type TEXT,
            field_number INTEGER,
            FOREIGN KEY(player_a_id) REFERENCES players(id),
            FOREIGN KEY(player_b_id) REFERENCES players(id),
            FOREIGN KEY(winner_id) REFERENCES players(id),
            FOREIGN KEY(session_id) REFERENCES sessions(id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Elo Rating System Functions
def calculate_expected_score(rating_a, rating_b):
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

def get_skill_level(elo_rating):
    if elo_rating < 1400:
        return 'Beginner'
    elif 1400 <= elo_rating < 1600:
        return 'Intermediate'
    else:
        return 'Advanced'

def get_k_factor(matches_played):
    if matches_played < 30:
        return 40
    else:
        return 20

def update_elo(player_a_id, player_b_id, winner_id, session_id, match_type, field_number):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Fetch current ratings and match counts
    cursor.execute('SELECT elo_rating, matches_played FROM players WHERE id = ?', (player_a_id,))
    result_a = cursor.fetchone()
    if not result_a:
        conn.close()
        return
    rating_a, matches_a = result_a

    cursor.execute('SELECT elo_rating, matches_played FROM players WHERE id = ?', (player_b_id,))
    result_b = cursor.fetchone()
    if not result_b:
        conn.close()
        return
    rating_b, matches_b = result_b

    # Calculate expected scores
    expected_a = calculate_expected_score(rating_a, rating_b)
    expected_b = calculate_expected_score(rating_b, rating_a)

    # Determine actual scores
    if winner_id == player_a_id:
        score_a, score_b = 1, 0
    elif winner_id == player_b_id:
        score_a, score_b = 0, 1
    else:
        score_a, score_b = 0.5, 0.5  # Handle draw if necessary

    # Determine K-factors
    k_a = get_k_factor(matches_a)
    k_b = get_k_factor(matches_b)

    # Update ratings
    new_rating_a = rating_a + k_a * (score_a - expected_a)
    new_rating_b = rating_b + k_b * (score_b - expected_b)

    # Update players' ratings and match counts
    cursor.execute('''
        UPDATE players 
        SET elo_rating = ?, matches_played = ?
        WHERE id = ?
    ''', (new_rating_a, matches_a + 1, player_a_id))
    cursor.execute('''
        UPDATE players 
        SET elo_rating = ?, matches_played = ?
        WHERE id = ?
    ''', (new_rating_b, matches_b + 1, player_b_id))

    # Update skill levels
    skill_a = get_skill_level(new_rating_a)
    skill_b = get_skill_level(new_rating_b)
    cursor.execute('''
        UPDATE players 
        SET skill_level = ?
        WHERE id = ?
    ''', (skill_a, player_a_id))
    cursor.execute('''
        UPDATE players 
        SET skill_level = ?
        WHERE id = ?
    ''', (skill_b, player_b_id))

    # Record the match
    cursor.execute('''
        INSERT INTO matches (date, session_id, player_a_id, player_b_id, score_a, score_b, winner_id, match_type, field_number)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), session_id, player_a_id, player_b_id,
          int(score_a), int(score_b), winner_id if winner_id else None, match_type, field_number))

    conn.commit()
    conn.close()

# Utility Functions
def get_player_names():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM players')
    names = [row[0] for row in cursor.fetchall()]
    conn.close()
    return names

def get_player_id(name):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM players WHERE name = ?', (name,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def get_player_name_by_id(player_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM players WHERE id = ?', (player_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else "N/A"

def get_leaderboard():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT name, elo_rating, skill_level FROM players
        ORDER BY elo_rating DESC
    ''')
    leaderboard = cursor.fetchall()
    conn.close()
    return leaderboard

def get_match_history():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT m.date, s.name, pa.name, pb.name, m.score_a, m.score_b, pw.name, m.match_type, m.field_number
        FROM matches m
        JOIN players pa ON m.player_a_id = pa.id
        JOIN players pb ON m.player_b_id = pb.id
        LEFT JOIN players pw ON m.winner_id = pw.id
        JOIN sessions s ON m.session_id = s.id
        ORDER BY m.date DESC
    ''')
    matches = cursor.fetchall()
    conn.close()
    return matches

def get_performance_data():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT name, elo_rating, matches_played, skill_level FROM players
    ''')
    players = cursor.fetchall()
    conn.close()

    # Calculate win rates
    performance_data = []
    for name, elo, matches_played, skill in players:
        if matches_played == 0:
            win_rate = 'N/A'
        else:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM matches 
                WHERE (player_a_id = (SELECT id FROM players WHERE name = ?) AND winner_id = player_a_id)
                   OR (player_b_id = (SELECT id FROM players WHERE name = ?) AND winner_id = player_b_id)
            ''', (name, name))
            wins = cursor.fetchone()[0]
            conn.close()
            win_rate = f"{(wins / matches_played * 100):.2f}%"
        performance_data.append((name, round(elo,2), matches_played, skill, win_rate))
    return performance_data

# Custom QListWidget for Assigned Players with Drag-and-Drop and Removal
class AssignedPlayersList(QListWidget):
    def __init__(self, available_list, parent=None):
        super().__init__(parent)
        self.available_list = available_list
        self.setAcceptDrops(True)
        self.setDragEnabled(False)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)  # Allow multiple selection

    def dropEvent(self, event):
        if event.source() == self.available_list:
            selected_items = self.available_list.selectedItems()
            for item in selected_items:
                player_name = item.text()
                # Prevent duplicate assignments
                if any(self.item(i).text() == player_name for i in range(self.count())):
                    QMessageBox.warning(self, 'Duplicate Player', f'Player "{player_name}" is already assigned.')
                    continue
                # Add to Assigned Players
                self.addItem(player_name)
                # Remove from Available Players
                self.available_list.takeItem(self.available_list.row(item))
        else:
            super().dropEvent(event)

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        if item:
            menu = QMenu(self)
            remove_action = menu.addAction("Remove Player")
            action = menu.exec_(self.mapToGlobal(event.pos()))
            if action == remove_action:
                player_name = item.text()
                # Remove from Assigned Players
                self.takeItem(self.row(item))
                # Add back to Available Players
                self.available_list.addItem(player_name)

# GUI Components
# Assuming you have a method to show the add player dialog
def show_add_player_dialog(self):
    dialog = QDialog(self)
    dialog.setWindowTitle("Add Player")
    
    form_layout = QFormLayout()
    
    name_input = QLineEdit()
    elo_input = QLineEdit()
    elo_input.setValidator(QDoubleValidator(0, 3000, 2))  # ELO rating between 0 and 3000 with 2 decimal places
    
    form_layout.addRow("Name:", name_input)
    form_layout.addRow("ELO Rating:", elo_input)
    
    buttons = QHBoxLayout()
    add_button = QPushButton("Add")
    cancel_button = QPushButton("Cancel")
    buttons.addWidget(add_button)
    buttons.addWidget(cancel_button)
    
    layout = QVBoxLayout()
    layout.addLayout(form_layout)
    layout.addLayout(buttons)
    
    dialog.setLayout(layout)
    
    def add_player():
        name = name_input.text()
        elo_rating = float(elo_input.text())
        
        if name and elo_rating:
            self.add_player_to_db(name, elo_rating)
            dialog.accept()
        else:
            QMessageBox.warning(self, "Input Error", "Please provide both name and ELO rating.")
    
    add_button.clicked.connect(add_player)
    cancel_button.clicked.connect(dialog.reject)
    
    dialog.exec_()

# Assuming you have a method to add a player to the database
def add_player_to_db(self, name, elo_rating):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO players (name, elo_rating)
            VALUES (?, ?)
        ''', (name, elo_rating))
        conn.commit()
    except sqlite3.IntegrityError:
        QMessageBox.warning(self, "Database Error", "Player with this name already exists.")
    finally:
        conn.close()

class ManagePlayersDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Manage Players')
        self.setGeometry(150, 150, 700, 500)
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()

        # Players Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(['ID', 'Name', 'Elo Rating', 'Skill Level', 'Availability'])
        self.load_players()
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        # Buttons
        button_layout = QHBoxLayout()
        self.add_button = QPushButton('Add Player')
        self.add_button.clicked.connect(self.add_player)
        self.remove_button = QPushButton('Remove Selected Player(s)')
        self.remove_button.clicked.connect(self.remove_players)
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.remove_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)
    
    def load_players(self):
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, elo_rating, skill_level, availability FROM players')
        players = cursor.fetchall()
        conn.close()

        self.table.setRowCount(len(players))
        for row_idx, (id_, name, elo, skill, availability) in enumerate(players):
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(id_)))
            self.table.setItem(row_idx, 1, QTableWidgetItem(name))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(round(elo, 2))))
            self.table.setItem(row_idx, 3, QTableWidgetItem(skill))
            self.table.setItem(row_idx, 4, QTableWidgetItem(availability if availability else "None"))

    def add_player(self):
        dialog = AddPlayerDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_players()
            # Optionally, emit a signal to refresh available players in ScheduleSessionDialog

    def remove_players(self):
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())
        if not selected_rows:
            QMessageBox.warning(self, 'Selection Error', 'Please select at least one player to remove.')
            return
        confirm = QMessageBox.question(
            self, 'Confirm Removal',
            f'Are you sure you want to remove {len(selected_rows)} player(s)?',
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            for row in selected_rows:
                player_id = int(self.table.item(row, 0).text())
                cursor.execute('DELETE FROM players WHERE id = ?', (player_id,))
            conn.commit()
            conn.close()
            QMessageBox.information(self, 'Success', 'Selected player(s) removed successfully.')
            self.load_players()
class AddPlayerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Add New Player')
        self.setGeometry(200, 200, 400, 300)
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()

        form_layout = QFormLayout()

        self.name_input = QLineEdit()
        form_layout.addRow('Name:', self.name_input)

        self.skill_combo = QComboBox()
        self.skill_combo.addItems(['Beginner', 'Intermediate', 'Advanced'])
        form_layout.addRow('Skill Level:', self.skill_combo)

        # Remove the availability input
        # self.availability_input = QLineEdit()
        # self.availability_input.setPlaceholderText('e.g., Monday, Wednesday')
        # form_layout.addRow('Availability:', self.availability_input)

        layout.addLayout(form_layout)

        self.submit_button = QPushButton('Add Player')
        self.submit_button.clicked.connect(self.add_player)
        layout.addWidget(self.submit_button)

        self.setLayout(layout)
    
    def add_player(self):
        name = self.name_input.text().strip()
        skill_level = self.skill_combo.currentText()

        if not name:
            QMessageBox.warning(self, 'Input Error', 'Player name cannot be empty.')
            return

        # Assign initial Elo rating based on skill level
        if skill_level == 'Beginner':
            elo = 1300
        elif skill_level == 'Intermediate':
            elo = 1500
        else:
            elo = 1700

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO players (name, elo_rating, skill_level)
                VALUES (?, ?, ?)
            ''', (name, elo, skill_level))
            conn.commit()
            QMessageBox.information(self, 'Success', f'Player "{name}" added successfully.')
            self.accept()
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, 'Error', f'Player "{name}" already exists.')
        finally:
            conn.close()

class ScheduleSessionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Schedule New Session')
        self.setGeometry(100, 100, 900, 700)  # Increased size to accommodate table
        self.session_id = None  # To keep track of the current session
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()

        form_layout = QFormLayout()

        self.match_type_combo = QComboBox()
        self.match_type_combo.addItems(['Singles', 'Doubles'])
        form_layout.addRow('Match Type:', self.match_type_combo)

        layout.addLayout(form_layout)

        # Drag and Drop Setup
        drag_drop_layout = QHBoxLayout()

        # Available Players List
        available_layout = QVBoxLayout()
        available_label = QLabel('Available Players:')
        self.available_list = QListWidget()
        self.available_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.available_list.setDragEnabled(True)
        available_layout.addWidget(available_label)
        available_layout.addWidget(self.available_list)
        drag_drop_layout.addLayout(available_layout)

        # Assigned Players List
        assigned_layout = QVBoxLayout()
        assigned_label = QLabel('Assigned Players:')
        self.assigned_list = AssignedPlayersList(self.available_list)
        assigned_layout.addWidget(assigned_label)
        assigned_layout.addWidget(self.assigned_list)
        drag_drop_layout.addLayout(assigned_layout)

        layout.addLayout(drag_drop_layout)

        # Populate Available Players
        self.populate_available_players()

        # Assuming you have a QTableWidget for scores
        self.scores_table = QTableWidget()
        self.scores_table.setColumnCount(4)
        self.scores_table.setHorizontalHeaderLabels(["Player A", "Player B", "Score A", "Score B"])

        # Example: Adding a row with editable score columns
        row_position = self.scores_table.rowCount()
        self.scores_table.insertRow(row_position)

        player_a_item = QTableWidgetItem("Player A Name")
        player_b_item = QTableWidgetItem("Player B Name")
        score_a_item = QTableWidgetItem("")
        score_b_item = QTableWidgetItem()

        # Make score columns editable
        score_a_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled)  # Make it editable
        score_b_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled)

        self.scores_table.setItem(row_position, 0, player_a_item)
        self.scores_table.setItem(row_position, 1, player_b_item)
        self.scores_table.setItem(row_position, 2, score_a_item)
        self.scores_table.setItem(row_position, 3, score_b_item)

        # Submit Button
        self.submit_button = QPushButton('Create Matchup')
        self.submit_button.clicked.connect(self.create_matchup)
        layout.addWidget(self.submit_button)

        # Matchups Display (Now using QTableWidget for score input)
        self.matchups_label = QLabel('Matchups:')
        layout.addWidget(self.matchups_label)

        self.matchups_table = QTableWidget()
        self.matchups_table.setColumnCount(5)  # Field, Team A, Team B, Score A, Score B
        self.matchups_table.setHorizontalHeaderLabels(['Field Number', 'Team A', 'Team B', 'Score A', 'Score B'])
        self.matchups_table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked)
        layout.addWidget(self.matchups_table)

        # Button to Submit Scores
        self.submit_scores_button = QPushButton('Submit Scores')
        self.submit_scores_button.clicked.connect(self.submit_scores)
        self.submit_scores_button.setEnabled(True)  # Disabled until a session is scheduled
        layout.addWidget(self.submit_scores_button)

        self.setLayout(layout)
    
    def populate_available_players(self):
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        # Fetch players with 'None' availability or those available today
        today_day = datetime.now().strftime('%A')  # e.g., 'Monday'
        # Handle cases where availability lists multiple days, ensuring partial matches
        cursor.execute('''
            SELECT name FROM players
            WHERE availability = 'None' 
               OR availability LIKE ?
               OR availability LIKE ?
               OR availability LIKE ?
        ''', (f'%{today_day}%', f'%, {today_day}', f'{today_day},%'))
        players = cursor.fetchall()
        conn.close()

        self.available_list.clear()
        for (name,) in players:
            item = QListWidgetItem(name)
            self.available_list.addItem(item)
    
    def create_matchup(self):
        match_type = self.match_type_combo.currentText()

        date_str = datetime.now().strftime('%Y-%m-%d')  # Current date

        assigned_players = []
        for index in range(self.assigned_list.count()):
            item = self.assigned_list.item(index)
            assigned_players.append(item.text())

        # Determine maximum players based on match type and fields
        if match_type == 'Singles':
            max_players = 2 * MAX_FIELDS  # 8 players
            required_players = 2
        else:
            max_players = 4 * MAX_FIELDS  # 16 players
            required_players = 4

        if len(assigned_players) < required_players:
            QMessageBox.warning(self, 'Input Error', f'At least {required_players} players are required for a {match_type} session.')
            return

        total_assigned = len(assigned_players)

        if total_assigned > max_players:
            # Assign only up to max_players to fields, rest to bench
            players_for_fields = assigned_players[:max_players]
            bench_players = assigned_players[max_players:]
        else:
            players_for_fields = assigned_players
            bench_players = []

        # Shuffle the players to randomize matchups
        random.shuffle(players_for_fields)

        # Assign a default session name based on current date and time
        session_name = f"Session on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        try:
            with sqlite3.connect(DATABASE) as conn:
                cursor = conn.cursor()

                # Insert new session
                cursor.execute('''
                    INSERT INTO sessions (name, match_type, date)
                    VALUES (?, ?, ?)
                ''', (session_name, match_type, date_str))
                session_id = cursor.lastrowid

                # Assign players to matches within the session
                matches = []
                if match_type == 'Singles':
                    for i in range(0, len(players_for_fields), 2):
                        if i + 1 < len(players_for_fields):
                            player_a = get_player_id(players_for_fields[i])
                            player_b = get_player_id(players_for_fields[i + 1])
                            matches.append((player_a, player_b))
                else:
                    for i in range(0, len(players_for_fields), 4):
                        if i + 3 < len(players_for_fields):
                            player_a = get_player_id(players_for_fields[i])
                            player_b = get_player_id(players_for_fields[i + 1])
                            player_c = get_player_id(players_for_fields[i + 2])
                            player_d = get_player_id(players_for_fields[i + 3])
                            matches.append((player_a, player_b, player_c, player_d))

                field_number = 1
                self.matchups_table.setRowCount(0)  # Clear any existing rows

                for match in matches:
                    if match_type == 'Singles':
                        player_a_id, player_b_id = match
                        player_a_name = get_player_name_by_id(player_a_id) if player_a_id else "N/A"
                        player_b_name = get_player_name_by_id(player_b_id) if player_b_id else "N/A"
                        cursor.execute('''
                            INSERT INTO matches (date, session_id, player_a_id, player_b_id, score_a, score_b, winner_id, match_type, field_number)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (date_str, session_id, player_a_id, player_b_id, 0, 0, None, match_type, field_number))
                        row_position = self.matchups_table.rowCount()
                        self.matchups_table.insertRow(row_position)
                        self.matchups_table.setItem(row_position, 0, QTableWidgetItem(str(field_number)))
                        self.matchups_table.setItem(row_position, 1, QTableWidgetItem(player_a_name))
                        self.matchups_table.setItem(row_position, 2, QTableWidgetItem(player_b_name))
                        self.matchups_table.setItem(row_position, 3, QTableWidgetItem(""))  # Score A
                        self.matchups_table.setItem(row_position, 4, QTableWidgetItem(""))  # Score B
                    else:
                        player_a_id, player_b_id, player_c_id, player_d_id = match
                        player_a_name = get_player_name_by_id(player_a_id) if player_a_id else "N/A"
                        player_b_name = get_player_name_by_id(player_b_id) if player_b_id else "N/A"
                        player_c_name = get_player_name_by_id(player_c_id) if player_c_id else "N/A"
                        player_d_name = get_player_name_by_id(player_d_id) if player_d_id else "N/A"
                        cursor.execute('''
                            INSERT INTO matches (date, session_id, player_a_id, player_b_id, score_a, score_b, winner_id, match_type, field_number)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (date_str, session_id, player_a_id, player_b_id, 0, 0, None, match_type, field_number))
                        row_position = self.matchups_table.rowCount()
                        self.matchups_table.insertRow(row_position)
                        self.matchups_table.setItem(row_position, 0, QTableWidgetItem(str(field_number)))
                        team_a = f"({player_a_name} & {player_b_name})"
                        team_b = f"({player_c_name} & {player_d_name})"
                        self.matchups_table.setItem(row_position, 1, QTableWidgetItem(team_a))
                        self.matchups_table.setItem(row_position, 2, QTableWidgetItem(team_b))
                        self.matchups_table.setItem(row_position, 3, QTableWidgetItem(""))  # Score A
                        self.matchups_table.setItem(row_position, 4, QTableWidgetItem(""))  # Score B
                    field_number += 1
                    if field_number > MAX_FIELDS:
                        field_number = 1  # Cycle through fields if more than MAX_FIELDS matches

                # Resize columns to fit the content
                for column in range(self.matchups_table.columnCount()):
                    self.matchups_table.resizeColumnToContents(column)

                if bench_players:
                    QMessageBox.information(self, 'Bench Players', f"The following players are on the bench:\n{', '.join(bench_players)}")
                else:
                    QMessageBox.information(self, 'Success', 'Session scheduled successfully.')

                self.submit_scores_button.setEnabled(True)  # Enable the submit scores button

        except sqlite3.OperationalError as e:
            QMessageBox.critical(self, 'Database Error', f'An error occurred while accessing the database: {str(e)}')

            
    
        def submit_scores(self):
            row_count = self.scores_table.rowCount()
            
            for row in range(row_count):
                player_a = self.scores_table.item(row, 0).text()
                player_b = self.scores_table.item(row, 1).text()
                score_a = self.scores_table.item(row, 2).text()
                score_b = self.scores_table.item(row, 3).text()
                
                # Process the scores (e.g., update the database, calculate new ELO ratings, etc.)
                self.process_scores(player_a, player_b, score_a, score_b)
    
        def process_scores(self, player_a, player_b, score_a, score_b):
            # Example processing logic
            try:
                score_a = int(score_a)
                score_b = int(score_b)
                
                # Update the database or perform other logic
                conn = sqlite3.connect(DATABASE)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO matches (player_a, player_b, score_a, score_b)
                    VALUES (?, ?, ?, ?)
                ''', (player_a, player_b, score_a, score_b))
                
                conn.commit()
                conn.close()
                
                # Update ELO ratings or other logic
                self.update_elo_ratings(player_a, player_b, score_a, score_b)
                
            except ValueError:
                QMessageBox.warning(self, "Input Error", "Scores must be integers.")
    
        def update_elo_ratings(self, player_a, player_b, score_a, score_b):
            # Implement ELO rating update logic here
            pass


    def submit_scores(self):
        row_count = self.matchups_table.rowCount()
        if row_count == 0:
            QMessageBox.warning(self, 'Error', 'No matches found to submit scores.')
            return

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        for row in range(row_count):
            field_number_item = self.matchups_table.item(row, 0)
            team_a_item = self.matchups_table.item(row, 1)
            team_b_item = self.matchups_table.item(row, 2)
            score_a_item = self.matchups_table.item(row, 3)
            score_b_item = self.matchups_table.item(row, 4)

            field_number = int(field_number_item.text()) if field_number_item.text().isdigit() else None
            team_a = team_a_item.text()
            team_b = team_b_item.text()
            score_a = score_a_item.text()
            score_b = score_b_item.text()

            # Validate scores
            if not score_a.isdigit() or not score_b.isdigit():
                QMessageBox.warning(self, 'Input Error', f'Please enter valid scores for Field {field_number}.')
                return

            score_a = int(score_a)
            score_b = int(score_b)

            # Determine winner
            if score_a > score_b:
                winner = team_a
            elif score_b > score_a:
                winner = team_b
            else:
                winner = None  # Handle draw if necessary

            # Fetch match_id from the database based on field_number
            cursor.execute('''
                SELECT id FROM matches
                WHERE field_number = ?
            ''', (field_number,))
            match = cursor.fetchone()
            
            if match:
                match_id = match[0]
                # Fetch player IDs based on team names
                if ' & ' in team_a and ' & ' in team_b:
                    # Doubles
                    players_a = team_a.replace('(', '').replace(')', '').split(' & ')
                    players_b = team_b.replace('(', '').replace(')', '').split(' & ')
                    player_a1_id = get_player_id(players_a[0])
                    player_a2_id = get_player_id(players_a[1])
                    player_b1_id = get_player_id(players_b[0])
                    player_b2_id = get_player_id(players_b[1])

                    # Update match scores and winner_id
                    if winner == team_a:
                        cursor.execute('''
                            UPDATE matches
                            SET score_a = ?, score_b = ?, winner_id = ?
                            WHERE id = ?
                        ''', (score_a, score_b, player_a1_id, match_id))
                    elif winner == team_b:
                        cursor.execute('''
                            UPDATE matches
                            SET score_a = ?, score_b = ?, winner_id = ?
                            WHERE id = ?
                        ''', (score_a, score_b, player_b1_id, match_id))
                    else:
                        # Handle draw if necessary
                        cursor.execute('''
                            UPDATE matches
                            SET score_a = ?, score_b = ?, winner_id = NULL
                            WHERE id = ?
                        ''', (score_a, score_b, match_id))
                else:
                    # Singles
                    player_a_id = get_player_id(team_a)
                    player_b_id = get_player_id(team_b)
                    if winner == team_a:
                        cursor.execute('''
                            UPDATE matches
                            SET score_a = ?, score_b = ?, winner_id = ?
                            WHERE id = ?
                        ''', (score_a, score_b, player_a_id, match_id))
                    elif winner == team_b:
                        cursor.execute('''
                            UPDATE matches
                            SET score_a = ?, score_b = ?, winner_id = ?
                            WHERE id = ?
                        ''', (score_a, score_b, player_b_id, match_id))
                    else:
                        cursor.execute('''
                            UPDATE matches
                            SET score_a = ?, score_b = ?, winner_id = NULL
                            WHERE id = ?
                        ''', (score_a, score_b, match_id))
            
        conn.commit()
        conn.close()

        # Update Elo ratings based on the submitted scores
        self.update_elo_ratings()

        QMessageBox.information(self, 'Success', 'Scores submitted and records updated successfully.')
        

    
    def update_elo_ratings(self):
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        # Fetch all matches in the latest session
        cursor.execute('''
            SELECT id, player_a_id, player_b_id, score_a, score_b, winner_id, match_type, field_number
            FROM matches
            WHERE session_id = (
                SELECT id FROM sessions ORDER BY id DESC LIMIT 1
            )
        ''')
        matches = cursor.fetchall()

        for match in matches:
            match_id, player_a_id, player_b_id, score_a, score_b, winner_id, match_type, field_number = match
            # Update Elo based on the scores
            if match_type == 'Singles':
                if score_a > score_b:
                    winner = player_a_id
                elif score_b > score_a:
                    winner = player_b_id
                else:
                    winner = None  # Draw
                update_elo(player_a_id, player_b_id, winner, session_id=None, match_type=match_type, field_number=field_number)
            else:
                # For doubles, determine winner based on team scores
                # Assuming team A is players_a and team B is players_b
                if score_a > score_b:
                    winner = player_a_id  # You can choose how to handle team wins
                elif score_b > score_a:
                    winner = player_b_id
                else:
                    winner = None  # Draw
                update_elo(player_a_id, player_b_id, winner, session_id=None, match_type=match_type, field_number=field_number)

        conn.close()

class LeaderboardWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Leaderboard')
        self.setGeometry(150, 150, 500, 400)
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(['Name', 'Elo Rating', 'Skill Level'])
        self.load_leaderboard()
        layout.addWidget(self.table)

        self.setLayout(layout)
    
    def load_leaderboard(self):
        leaderboard = get_leaderboard()
        self.table.setRowCount(len(leaderboard))
        for row_idx, (name, elo, skill) in enumerate(leaderboard):
            self.table.setItem(row_idx, 0, QTableWidgetItem(name))
            self.table.setItem(row_idx, 1, QTableWidgetItem(str(round(elo, 2))))
            self.table.setItem(row_idx, 2, QTableWidgetItem(skill))

class MatchHistoryWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Match History')
        self.setGeometry(150, 150, 800, 500)
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            'Date', 'Session', 'Player A', 'Player B',
            'Score A', 'Score B', 'Winner', 'Match Type', 'Field Number'
        ])
        self.load_match_history()
        layout.addWidget(self.table)

        self.setLayout(layout)
    
    def load_match_history(self):
        matches = get_match_history()
        self.table.setRowCount(len(matches))
        for row_idx, (date, session, pa, pb, sa, sb, pw, mt, fn) in enumerate(matches):
            self.table.setItem(row_idx, 0, QTableWidgetItem(date))
            self.table.setItem(row_idx, 1, QTableWidgetItem(session))
            self.table.setItem(row_idx, 2, QTableWidgetItem(pa))
            self.table.setItem(row_idx, 3, QTableWidgetItem(pb))
            self.table.setItem(row_idx, 4, QTableWidgetItem(str(sa)))
            self.table.setItem(row_idx, 5, QTableWidgetItem(str(sb)))
            self.table.setItem(row_idx, 6, QTableWidgetItem(pw if pw else "N/A"))
            self.table.setItem(row_idx, 7, QTableWidgetItem(mt))
            self.table.setItem(row_idx, 8, QTableWidgetItem(str(fn) if fn else 'N/A'))

class PerformanceTrackingWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Performance Tracking')
        self.setGeometry(150, 150, 600, 500)
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(['Name', 'Elo Rating', 'Matches Played', 'Skill Level', 'Win Rate'])
        self.load_performance_data()
        layout.addWidget(self.table)

        self.setLayout(layout)
    
    def load_performance_data(self):
        performance_data = get_performance_data()
        self.table.setRowCount(len(performance_data))
        for row_idx, (name, elo, mp, skill, wr) in enumerate(performance_data):
            self.table.setItem(row_idx, 0, QTableWidgetItem(name))
            self.table.setItem(row_idx, 1, QTableWidgetItem(str(elo)))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(mp)))
            self.table.setItem(row_idx, 3, QTableWidgetItem(skill))
            self.table.setItem(row_idx, 4, QTableWidgetItem(wr))

class ImportPlayersDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Import Players from CSV')
        self.setGeometry(150, 150, 500, 200)
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()

        self.file_label = QLabel('Select CSV File:')
        self.file_path = QLineEdit()
        self.browse_button = QPushButton('Browse')
        self.browse_button.clicked.connect(self.browse_file)

        file_layout = QHBoxLayout()
        file_layout.addWidget(self.file_path)
        file_layout.addWidget(self.browse_button)
        layout.addWidget(self.file_label)
        layout.addLayout(file_layout)

        self.import_button = QPushButton('Import Players')
        self.import_button.clicked.connect(self.import_players)
        layout.addWidget(self.import_button)

        self.setLayout(layout)
    
    def browse_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, 'Open CSV File', '', 'CSV Files (*.csv)')
        if file_name:
            self.file_path.setText(file_name)
    
    def import_players(self):
        file_path = self.file_path.text().strip()
        if not file_path:
            QMessageBox.warning(self, 'Input Error', 'Please select a CSV file.')
            return

        try:
            with open(file_path, newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                conn = sqlite3.connect(DATABASE)
                cursor = conn.cursor()
                for row in reader:
                    name = row['name'].strip()
                    skill_level = row.get('skill_level', 'Beginner').strip()
                    availability = row.get('availability', 'None').strip()

                    # Assign initial Elo rating based on skill level
                    if skill_level == 'Beginner':
                        elo = 1300
                    elif skill_level == 'Intermediate':
                        elo = 1500
                    else:
                        elo = 1700

                    cursor.execute('''
                        INSERT OR IGNORE INTO players (name, elo_rating, skill_level, availability)
                        VALUES (?, ?, ?, ?)
                    ''', (name, elo, skill_level, availability if availability else 'None'))
                conn.commit()
                conn.close()
            QMessageBox.information(self, 'Success', 'Players imported successfully.')
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to import players.\nError: {str(e)}')

class RecordMatchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Record Match Result')
        self.setGeometry(100, 100, 400, 300)
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()

        # Player A Selection
        self.player_a_label = QLabel('Player A:')
        self.player_a_combo = QComboBox()
        self.player_a_combo.addItems(get_player_names())
        layout.addWidget(self.player_a_label)
        layout.addWidget(self.player_a_combo)

        # Player B Selection
        self.player_b_label = QLabel('Player B:')
        self.player_b_combo = QComboBox()
        self.player_b_combo.addItems(get_player_names())
        layout.addWidget(self.player_b_label)
        layout.addWidget(self.player_b_combo)

        # Winner Selection
        self.winner_label = QLabel('Winner:')
        self.winner_combo = QComboBox()
        self.winner_combo.addItems(['Player A', 'Player B'])
        layout.addWidget(self.winner_label)
        layout.addWidget(self.winner_combo)

        # Submit Button
        self.submit_button = QPushButton('Submit Result')
        self.submit_button.clicked.connect(self.submit_result)
        layout.addWidget(self.submit_button)

        self.setLayout(layout)
    
    def submit_result(self):
        player_a_name = self.player_a_combo.currentText()
        player_b_name = self.player_b_combo.currentText()
        winner = self.winner_combo.currentText()

        if player_a_name == player_b_name:
            QMessageBox.warning(self, 'Input Error', 'Player A and Player B cannot be the same.')
            return

        player_a_id = get_player_id(player_a_name)
        player_b_id = get_player_id(player_b_name)
        winner_id = player_a_id if winner == 'Player A' else player_b_id

        # Assuming match_type as 'Singles' and field_number as None since it's manually recorded
        update_elo(player_a_id, player_b_id, winner_id, session_id=None, match_type='Singles', field_number=None)

        QMessageBox.information(self, 'Success', 'Match result recorded successfully.')
        self.accept()

class LeaderboardWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Leaderboard')
        self.setGeometry(150, 150, 500, 400)
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(['Name', 'Elo Rating', 'Skill Level'])
        self.load_leaderboard()
        layout.addWidget(self.table)

        self.setLayout(layout)
    
    def load_leaderboard(self):
        leaderboard = get_leaderboard()
        self.table.setRowCount(len(leaderboard))
        for row_idx, (name, elo, skill) in enumerate(leaderboard):
            self.table.setItem(row_idx, 0, QTableWidgetItem(name))
            self.table.setItem(row_idx, 1, QTableWidgetItem(str(round(elo, 2))))
            self.table.setItem(row_idx, 2, QTableWidgetItem(skill))

class MatchHistoryWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Match History')
        self.setGeometry(150, 150, 800, 500)
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            'Date', 'Session', 'Player A', 'Player B',
            'Score A', 'Score B', 'Winner', 'Match Type', 'Field Number'
        ])
        self.load_match_history()
        layout.addWidget(self.table)

        self.setLayout(layout)
    
    def load_match_history(self):
        matches = get_match_history()
        self.table.setRowCount(len(matches))
        for row_idx, (date, session, pa, pb, sa, sb, pw, mt, fn) in enumerate(matches):
            self.table.setItem(row_idx, 0, QTableWidgetItem(date))
            self.table.setItem(row_idx, 1, QTableWidgetItem(session))
            self.table.setItem(row_idx, 2, QTableWidgetItem(pa))
            self.table.setItem(row_idx, 3, QTableWidgetItem(pb))
            self.table.setItem(row_idx, 4, QTableWidgetItem(str(sa)))
            self.table.setItem(row_idx, 5, QTableWidgetItem(str(sb)))
            self.table.setItem(row_idx, 6, QTableWidgetItem(pw if pw else "N/A"))
            self.table.setItem(row_idx, 7, QTableWidgetItem(mt))
            self.table.setItem(row_idx, 8, QTableWidgetItem(str(fn) if fn else 'N/A'))

class PerformanceTrackingWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Performance Tracking')
        self.setGeometry(150, 150, 600, 500)
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(['Name', 'Elo Rating', 'Matches Played', 'Skill Level', 'Win Rate'])
        self.load_performance_data()
        layout.addWidget(self.table)

        self.setLayout(layout)
    
    def load_performance_data(self):
        performance_data = get_performance_data()
        self.table.setRowCount(len(performance_data))
        for row_idx, (name, elo, mp, skill, wr) in enumerate(performance_data):
            self.table.setItem(row_idx, 0, QTableWidgetItem(name))
            self.table.setItem(row_idx, 1, QTableWidgetItem(str(elo)))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(mp)))
            self.table.setItem(row_idx, 3, QTableWidgetItem(skill))
            self.table.setItem(row_idx, 4, QTableWidgetItem(wr))

class ImportPlayersDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Import Players from CSV')
        self.setGeometry(150, 150, 500, 200)
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()

        self.file_label = QLabel('Select CSV File:')
        self.file_path = QLineEdit()
        self.browse_button = QPushButton('Browse')
        self.browse_button.clicked.connect(self.browse_file)

        file_layout = QHBoxLayout()
        file_layout.addWidget(self.file_path)
        file_layout.addWidget(self.browse_button)
        layout.addWidget(self.file_label)
        layout.addLayout(file_layout)

        self.import_button = QPushButton('Import Players')
        self.import_button.clicked.connect(self.import_players)
        layout.addWidget(self.import_button)

        self.setLayout(layout)
    
    def browse_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, 'Open CSV File', '', 'CSV Files (*.csv)')
        if file_name:
            self.file_path.setText(file_name)
    
    def import_players(self):
        file_path = self.file_path.text().strip()
        if not file_path:
            QMessageBox.warning(self, 'Input Error', 'Please select a CSV file.')
            return

        try:
            with open(file_path, newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                conn = sqlite3.connect(DATABASE)
                cursor = conn.cursor()
                for row in reader:
                    name = row['name'].strip()
                    skill_level = row.get('skill_level', 'Beginner').strip()
                    availability = row.get('availability', 'None').strip()

                    # Assign initial Elo rating based on skill level
                    if skill_level == 'Beginner':
                        elo = 1300
                    elif skill_level == 'Intermediate':
                        elo = 1500
                    else:
                        elo = 1700

                    cursor.execute('''
                        INSERT OR IGNORE INTO players (name, elo_rating, skill_level, availability)
                        VALUES (?, ?, ?, ?)
                    ''', (name, elo, skill_level, availability if availability else 'None'))
                conn.commit()
                conn.close()
            QMessageBox.information(self, 'Success', 'Players imported successfully.')
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to import players.\nError: {str(e)}')

class RecordMatchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Record Match Result')
        self.setGeometry(100, 100, 400, 300)
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()

        # Player A Selection
        self.player_a_label = QLabel('Player A:')
        self.player_a_combo = QComboBox()
        self.player_a_combo.addItems(get_player_names())
        layout.addWidget(self.player_a_label)
        layout.addWidget(self.player_a_combo)

        # Player B Selection
        self.player_b_label = QLabel('Player B:')
        self.player_b_combo = QComboBox()
        self.player_b_combo.addItems(get_player_names())
        layout.addWidget(self.player_b_label)
        layout.addWidget(self.player_b_combo)

        # Winner Selection
        self.winner_label = QLabel('Winner:')
        self.winner_combo = QComboBox()
        self.winner_combo.addItems(['Player A', 'Player B'])
        layout.addWidget(self.winner_label)
        layout.addWidget(self.winner_combo)

        # Submit Button
        self.submit_button = QPushButton('Submit Result')
        self.submit_button.clicked.connect(self.submit_result)
        layout.addWidget(self.submit_button)

        self.setLayout(layout)
    
    def submit_result(self):
        player_a_name = self.player_a_combo.currentText()
        player_b_name = self.player_b_combo.currentText()
        winner = self.winner_combo.currentText()

        if player_a_name == player_b_name:
            QMessageBox.warning(self, 'Input Error', 'Player A and Player B cannot be the same.')
            return

        player_a_id = get_player_id(player_a_name)
        player_b_id = get_player_id(player_b_name)
        winner_id = player_a_id if winner == 'Player A' else player_b_id

        # Assuming match_type as 'Singles' and field_number as None since it's manually recorded
        update_elo(player_a_id, player_b_id, winner_id, session_id=None, match_type='Singles', field_number=None)

        QMessageBox.information(self, 'Success', 'Match result recorded successfully.')
        self.accept()

class LeaderboardWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Leaderboard')
        self.setGeometry(150, 150, 500, 400)
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(['Name', 'Elo Rating', 'Skill Level'])
        self.load_leaderboard()
        layout.addWidget(self.table)

        self.setLayout(layout)
    
    def load_leaderboard(self):
        leaderboard = get_leaderboard()
        self.table.setRowCount(len(leaderboard))
        for row_idx, (name, elo, skill) in enumerate(leaderboard):
            self.table.setItem(row_idx, 0, QTableWidgetItem(name))
            self.table.setItem(row_idx, 1, QTableWidgetItem(str(round(elo, 2))))
            self.table.setItem(row_idx, 2, QTableWidgetItem(skill))

class MatchHistoryWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Match History')
        self.setGeometry(150, 150, 800, 500)
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            'Date', 'Session', 'Player A', 'Player B',
            'Score A', 'Score B', 'Winner', 'Match Type', 'Field Number'
        ])
        self.load_match_history()
        layout.addWidget(self.table)

        self.setLayout(layout)
    
    def load_match_history(self):
        matches = get_match_history()
        self.table.setRowCount(len(matches))
        for row_idx, (date, session, pa, pb, sa, sb, pw, mt, fn) in enumerate(matches):
            self.table.setItem(row_idx, 0, QTableWidgetItem(date))
            self.table.setItem(row_idx, 1, QTableWidgetItem(session))
            self.table.setItem(row_idx, 2, QTableWidgetItem(pa))
            self.table.setItem(row_idx, 3, QTableWidgetItem(pb))
            self.table.setItem(row_idx, 4, QTableWidgetItem(str(sa)))
            self.table.setItem(row_idx, 5, QTableWidgetItem(str(sb)))
            self.table.setItem(row_idx, 6, QTableWidgetItem(pw if pw else "N/A"))
            self.table.setItem(row_idx, 7, QTableWidgetItem(mt))
            self.table.setItem(row_idx, 8, QTableWidgetItem(str(fn) if fn else 'N/A'))

class PerformanceTrackingWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Performance Tracking')
        self.setGeometry(150, 150, 600, 500)
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(['Name', 'Elo Rating', 'Matches Played', 'Skill Level', 'Win Rate'])
        self.load_performance_data()
        layout.addWidget(self.table)

        self.setLayout(layout)
    
    def load_performance_data(self):
        performance_data = get_performance_data()
        self.table.setRowCount(len(performance_data))
        for row_idx, (name, elo, mp, skill, wr) in enumerate(performance_data):
            self.table.setItem(row_idx, 0, QTableWidgetItem(name))
            self.table.setItem(row_idx, 1, QTableWidgetItem(str(elo)))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(mp)))
            self.table.setItem(row_idx, 3, QTableWidgetItem(skill))
            self.table.setItem(row_idx, 4, QTableWidgetItem(wr))

# Main Application Window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Badminton Match-Up App')
        self.setGeometry(100, 100, 400, 600)
        self.initUI()
    
    def initUI(self):
        central_widget = QWidget()
        layout = QVBoxLayout()

        # Manage Players Button
        self.manage_players_button = QPushButton('Manage Players')
        self.manage_players_button.clicked.connect(self.open_manage_players)
        layout.addWidget(self.manage_players_button)

        # Import Players Button
        self.import_players_button = QPushButton('Import Players from CSV')
        self.import_players_button.clicked.connect(self.open_import_players)
        layout.addWidget(self.import_players_button)

        # Record Match Result Button
        self.record_match_button = QPushButton('Record Match Result')
        self.record_match_button.clicked.connect(self.open_record_match)
        layout.addWidget(self.record_match_button)

        # View Leaderboard Button
        self.leaderboard_button = QPushButton('View Leaderboard')
        self.leaderboard_button.clicked.connect(self.open_leaderboard)
        layout.addWidget(self.leaderboard_button)

        # View Match History Button
        self.match_history_button = QPushButton('View Match History')
        self.match_history_button.clicked.connect(self.open_match_history)
        layout.addWidget(self.match_history_button)

        # View Performance Tracking Button
        self.performance_button = QPushButton('View Performance Tracking')
        self.performance_button.clicked.connect(self.open_performance_tracking)
        layout.addWidget(self.performance_button)

        # Schedule New Session Button
        self.create_matchup_button = QPushButton('Generate Matchups')
        self.create_matchup_button.clicked.connect(self.open_create_matchup)
        layout.addWidget(self.create_matchup_button)

        # Add Stretch to push buttons to the top
        layout.addStretch()

        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
    
    def open_manage_players(self):
        dialog = ManagePlayersDialog(self)
        dialog.exec_()
    
    def open_import_players(self):
        dialog = ImportPlayersDialog(self)
        dialog.exec_()
    
    def open_record_match(self):
        dialog = RecordMatchDialog(self)
        dialog.exec_()
    
    def open_leaderboard(self):
        window = LeaderboardWindow(self)
        window.exec_()
    
    def open_match_history(self):
        window = MatchHistoryWindow(self)
        window.exec_()
    
    def open_performance_tracking(self):
        window = PerformanceTrackingWindow(self)
        window.exec_()
    
    def open_create_matchup(self):
        dialog = ScheduleSessionDialog(self)
        dialog.exec_()

# Main Execution
if __name__ == "__main__":
    init_db()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())