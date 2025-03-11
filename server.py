from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS  # Import CORS
import pandas as pd
from datetime import datetime
import os

app = Flask(__name__, static_folder='./build', static_url_path='/')
CORS(app)  # Enable CORS for all routes

# Define CSV file paths
FIRST_STAGE_CSV = 'data/csv1.csv'
SECOND_STAGE_CSV = 'data/csv2.csv'
FIRST_STAGE_ENTRIES_CSV = 'data/csv3.csv'
SECOND_STAGE_ENTRIES_CSV = 'data/csv4.csv'

# Ensure data directory exists
os.makedirs('data', exist_ok=True)

# Initialize CSV files if they don't exist
def initialize_csv_files():
    # Initialize first stage credentials CSV (csv1.csv)
    if not os.path.exists(FIRST_STAGE_CSV):
        pd.DataFrame({
            'team_number': ['001', '002', '003'],
            'passcode': ['alpha123', 'beta456', 'gamma789']
        }).to_csv(FIRST_STAGE_CSV, index=False)
    
    # Initialize second stage credentials CSV (csv2.csv)
    if not os.path.exists(SECOND_STAGE_CSV):
        pd.DataFrame({
            'team_number': ['001', '002', '003'],
            'passcode': ['delta321', 'epsilon654', 'zeta987']
        }).to_csv(SECOND_STAGE_CSV, index=False)
    
    # Initialize entries CSVs
    for csv_file in [FIRST_STAGE_ENTRIES_CSV, SECOND_STAGE_ENTRIES_CSV]:
        if not os.path.exists(csv_file):
            pd.DataFrame(columns=['team_number', 'timestamp']).to_csv(csv_file, index=False)

# Initialize CSV files on startup
initialize_csv_files()

# Serve React app
@app.route('/')
def serve():
    return send_from_directory(app.static_folder, 'index.html')

# Fallback for all other routes to serve React app
@app.route('/<path:path>')
def serve_any(path):
    try:
        return send_from_directory(app.static_folder, path)
    except:
        return send_from_directory(app.static_folder, 'index.html')

# API endpoint to verify first stage credentials
@app.route('/api/verify-first-stage', methods=['POST'])
def verify_first_stage():
    data = request.json
    team_number = str(data.get('teamNumber')).strip()
    passcode = str(data.get('passcode')).strip()
    
    # Debug prints
    print(f"Received: team={team_number}, passcode={passcode}")
    
    try:
        df = pd.read_csv(FIRST_STAGE_CSV)
        
        # Convert dataframe columns to strings and strip whitespace
        df['team_number'] = df['team_number'].astype(str).str.strip()
        df['passcode'] = df['passcode'].astype(str).str.strip()
        
        # Debug prints
        print("Available credentials in CSV:")
        for _, row in df.iterrows():
            print(f"  team={row['team_number']}, passcode={row['passcode']}")
        
        # Verify credentials
        matched = df[(df['team_number'] == team_number) & (df['passcode'] == passcode)]
        
        if not matched.empty:
            # Record successful entry in csv3
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            entry_df = pd.read_csv(FIRST_STAGE_ENTRIES_CSV)
            new_entry = pd.DataFrame([{'team_number': team_number, 'timestamp': timestamp}])
            entry_df = pd.concat([entry_df, new_entry])
            entry_df.to_csv(FIRST_STAGE_ENTRIES_CSV, index=False)
            
            return jsonify({'success': True})
        else:
            print(f"No match found for team={team_number}, passcode={passcode}")
            return jsonify({'success': False, 'message': 'Invalid credentials'})
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# API endpoint to verify second stage credentials
@app.route('/api/verify-second-stage', methods=['POST'])
def verify_second_stage():
    data = request.json
    team_number = str(data.get('teamNumber')).strip()
    passcode = str(data.get('passcode')).strip()
    
    # Debug prints
    print(f"Received: team={team_number}, passcode={passcode}")
    
    try:
        df = pd.read_csv(SECOND_STAGE_CSV)
        
        # Convert dataframe columns to strings and strip whitespace
        df['team_number'] = df['team_number'].astype(str).str.strip()
        df['passcode'] = df['passcode'].astype(str).str.strip()
        
        # Debug prints
        print("Available credentials in CSV:")
        for _, row in df.iterrows():
            print(f"  team={row['team_number']}, passcode={row['passcode']}")
        
        # Verify credentials
        matched = df[(df['team_number'] == team_number) & (df['passcode'] == passcode)]
        
        if not matched.empty:
            # Record successful entry in csv4
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            entry_df = pd.read_csv(SECOND_STAGE_ENTRIES_CSV)
            new_entry = pd.DataFrame([{'team_number': team_number, 'timestamp': timestamp}])
            entry_df = pd.concat([entry_df, new_entry])
            entry_df.to_csv(SECOND_STAGE_ENTRIES_CSV, index=False)
            
            return jsonify({'success': True})
        else:
            print(f"No match found for team={team_number}, passcode={passcode}")
            return jsonify({'success': False, 'message': 'Invalid credentials'})
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)