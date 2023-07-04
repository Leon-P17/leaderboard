import sqlite3
import os
import webbrowser
import pandas as pd
import difflib
import re
from flask import Flask, render_template, request, jsonify, redirect, url_for
from tkinter import filedialog
from fuzzywuzzy import fuzz

app = Flask(__name__, static_folder='static')
DATABASE = 'leaderboard.db'

def create_tables():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Create drivers database
    cursor.execute('''CREATE TABLE IF NOT EXISTS drivers
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       name TEXT,
                       first_name TEXT,
                       last_name TEXT,
                       lap_time REAL)''')
    conn.commit()
    conn.close()

def get_leaderboard():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT name, lap_time FROM drivers ORDER BY lap_time ASC')
    leaderboard = [{'name': format_driver_name(row[0]), 'lap_time': format_lap_time(row[1])} for row in cursor.fetchall()]
    conn.close()
    return leaderboard

def format_driver_name(full_name):
    names = full_name.split()
    if len(names) == 1:
        return names[0]
    else:
        return f"{names[0]} {names[1][0]}"

def format_lap_time(lap_time):
    if isinstance(lap_time, str):
        # Check for different formats of lap time
        if ':' in lap_time:
            # Format: minutes:seconds.milliseconds or minutes:seconds:milliseconds
            parts = lap_time.split(':')
            if len(parts) == 3:
                minutes, seconds, milliseconds = parts
            elif len(parts) == 2:
                minutes, seconds = parts
                milliseconds = '000'
            else:
                return lap_time  # Invalid format, return as is
        else:
            # Format: seconds.milliseconds or milliseconds
            parts = lap_time.split('.')
            if len(parts) == 2:
                seconds, milliseconds = parts
                minutes = '0'
            else:
                return lap_time  # Invalid format, return as is

        try:
            minutes = int(minutes)
            seconds = int(seconds)
            milliseconds = int(milliseconds)
        except ValueError:
            return lap_time  # Invalid format, return as is

        # Perform the necessary conversions and formatting
        formatted_time = f"{minutes}:{seconds:02d}.{milliseconds:03d}"
        return formatted_time
    elif isinstance(lap_time, (int, float)):
        # Convert seconds to "minutes:seconds:milliseconds" format
        minutes = int(lap_time // 60)
        seconds = int(lap_time % 60)
        milliseconds = int((lap_time % 1) * 1000)
        formatted_time = f"{minutes}:{seconds:02d}.{milliseconds:03d}"
        return formatted_time
    else:
        return lap_time

def add_driver(name, lap_time):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT lap_time FROM drivers WHERE name = ?', (name,))
    existing_lap_time = cursor.fetchone()

    if existing_lap_time is None or lap_time < existing_lap_time[0]:
        cursor.execute('DELETE FROM drivers WHERE name = ?', (name,))
        # Split the name into first name and last name
        names = name.split()
        first_name = names[0]
        last_name = names[-1]
        cursor.execute('INSERT INTO drivers (name, first_name, last_name, lap_time) VALUES (?, ?, ?, ?)',
                       (name, first_name, last_name, lap_time))
        conn.commit()

    # Fetch the updated leaderboard
    cursor.execute('SELECT name, lap_time FROM drivers ORDER BY lap_time ASC')
    leaderboard = [{'name': format_driver_name(row[0]), 'lap_time': format_lap_time(row[1])} for row in cursor.fetchall()]

    conn.close()
    return leaderboard

def clear_leaderboard():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM drivers')
    conn.commit()
    conn.close()

def parse_lap_time(lap_time_str):
    # Regular expression pattern to match lap time components
    pattern = r'(\d+)[.:](\d+)[.:](\d+)'

    match = re.match(pattern, lap_time_str)
    if match:
        minutes = int(match.group(1))
        seconds = int(match.group(2))
        milliseconds = int(match.group(3))
        total_seconds = minutes * 60 + seconds + milliseconds / 1000.0
        return total_seconds
    else:
        raise ValueError('Invalid lap time format')

def find_lap_time_column(sheet):
    lap_time_column = None
    for column in sheet.iter_cols(min_row=1, max_row=1):
        for cell in column:
            if cell.value in ['Lap Time', 'lap_time', 'LapTime', 'Lap', 'Time']:
                lap_time_column = cell.column_letter
                break
        if lap_time_column:
            break
    return lap_time_column

def find_column_by_name(df, target_column_name):
    max_similarity = -1
    matched_column = None
    for col in df.columns:
        similarity = fuzz.ratio(target_column_name, str(col).lower())
        if similarity > max_similarity:
            max_similarity = similarity
            matched_column = col
    return matched_column

def rename_columns(df, name_column, lap_time_column):
    df = df.rename(columns={name_column: 'name', lap_time_column: 'lap_time'})
    return df

def process_excel_file(df):
    # Find the column containing the driver name
    name_column = None
    for col in df.columns:
        if 'name' in str(col).lower():
            name_column = col
            break

    if name_column is None:
        # Attempt to find similar column names
        possible_name_columns = difflib.get_close_matches('name', df.columns)
        if possible_name_columns:
            name_column = possible_name_columns[0]

    # Find the column containing the lap time
    lap_time_column = find_column_by_name(df, 'lap time')

    if name_column is None or lap_time_column is None:
        return None, None

    # Rename headers
    df = rename_columns(df, name_column, lap_time_column)

    return df['name'], df['lap_time']


# Routes

@app.route('/')
def main():
    return render_template('main.html')

@app.route('/leaderboard')
def leaderboard():
    leaderboard_data = get_leaderboard()
    return render_template('leaderboard.html', leaderboard=leaderboard_data)

@app.route('/control_panel', methods=['GET', 'POST'])
def control_panel():
    if request.method == 'POST':
        name = request.form['name']
        lap_time_str = request.form['lap_time']
        lap_time = parse_lap_time(lap_time_str)

        if add_driver(name, lap_time):
            return redirect('/leaderboard')
        else:
            return render_template('control_panel.html')

    return render_template('control_panel.html')

@app.route('/add_driver', methods=['POST'])
def add_driver_route():
    name = request.form['name']
    lap_time_str = request.form['lap_time']
    lap_time = parse_lap_time(lap_time_str)

    if add_driver(name, lap_time):
        return redirect(url_for('control_panel'))
    else:
        return redirect(url_for('control_panel'))

@app.route('/clear_leaderboard', methods=['POST'])
def clear_leaderboard_route():
    clear_leaderboard()
    return jsonify(confirm=True)

@app.route('/stop_program', methods=['POST'])
def stop_program():
    os.kill(os.getpid(), 9)

# Route for uploading Excel file
@app.route('/upload_drivers', methods=['POST'])
def upload_drivers_route():
    file = request.files['file']
    if file:
        try:
            # Read the Excel file
            df = pd.read_excel(file)

            # Extract column data
            name_column, lap_time_column = process_excel_file(df)

            if name_column is None or lap_time_column is None:
                error_message = "Could not find the required columns 'name' and 'lap_time' in the Excel file."
                return render_template('control_panel.html', error_message=error_message)

            # Connect to the database
            conn = sqlite3.connect(DATABASE)

            # Add drivers to the leaderboard
            for name, lap_time in zip(name_column, lap_time_column):
                formatted_lap_time = format_lap_time(lap_time)
                add_driver(name, formatted_lap_time)

            # Commit the changes and close the connection
            conn.commit()
            conn.close()

        except Exception as e:
            print(f"Error uploading Excel file: {e}", flush=True)

    return redirect(url_for('control_panel'))


if __name__ == '__main__':
    create_tables()
    webbrowser.open('http://localhost:5000')
    app.run()
