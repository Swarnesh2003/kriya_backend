from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
from datetime import datetime
import os

app = Flask(__name__, static_folder='./build', static_url_path='/')
CORS(app)

# Define CSV file paths
FIRST_STAGE_CSV = 'data/csv1.csv'
SECOND_STAGE_CSV = 'data/csv2.csv'
FIRST_STAGE_ENTRIES_CSV = 'data/csv3.csv'
SECOND_STAGE_ENTRIES_CSV = 'data/csv4.csv'

# Mapping of CSV IDs to file paths
CSV_MAPPING = {
    'first-stage-credentials': FIRST_STAGE_CSV,
    'second-stage-credentials': SECOND_STAGE_CSV,
    'first-stage-entries': FIRST_STAGE_ENTRIES_CSV,
    'second-stage-entries': SECOND_STAGE_ENTRIES_CSV
}

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
        # Load the credentials database
        df = pd.read_csv(SECOND_STAGE_CSV)
        
        # Convert dataframe columns to strings and strip whitespace
        df['team_number'] = df['team_number'].astype(str).str.strip()
        df['passcode'] = df['passcode'].astype(str).str.strip()
        
        # Debug prints
        print("Available credentials in CSV:")
        for _, row in df.iterrows():
            print(f"  team={row['team_number']}, passcode={row['passcode']}")
        
        # Load the attempts tracking data
        attempts_file = 'attempts_tracking.csv'
        
        # Create attempts file if it doesn't exist
        if not os.path.exists(attempts_file):
            pd.DataFrame(columns=['team_number', 'attempts']).to_csv(attempts_file, index=False)
        
        attempts_df = pd.read_csv(attempts_file)
        
        # Ensure attempts_df has the correct structure
        if 'team_number' not in attempts_df.columns:
            attempts_df['team_number'] = []
        if 'attempts' not in attempts_df.columns:
            attempts_df['attempts'] = []
        
        # Convert team_number to string for matching
        attempts_df['team_number'] = attempts_df['team_number'].astype(str).str.strip()
        
        # Check if team exists in attempts_df, if not, add it
        if team_number not in attempts_df['team_number'].values:
            new_team = pd.DataFrame([{'team_number': team_number, 'attempts': 1}])
            attempts_df = pd.concat([attempts_df, new_team])
        else:
            # Increment attempts count for this team
            attempts_df.loc[attempts_df['team_number'] == team_number, 'attempts'] += 1
        
        # Save updated attempts count
        attempts_df.to_csv(attempts_file, index=False)
        
        # Get current attempts count for this team
        current_attempts = attempts_df.loc[attempts_df['team_number'] == team_number, 'attempts'].values[0]
        
        # Verify credentials
        matched = df[(df['team_number'] == team_number) & (df['passcode'] == passcode)]
        
        if not matched.empty:
            # Record successful entry with attempts count
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            entry_df = pd.read_csv(SECOND_STAGE_ENTRIES_CSV)
            
            # Add attempts data to the entry
            new_entry = pd.DataFrame([{
                'team_number': team_number, 
                'timestamp': timestamp,
                'attempts': current_attempts
            }])
            
            entry_df = pd.concat([entry_df, new_entry])
            entry_df.to_csv(SECOND_STAGE_ENTRIES_CSV, index=False)
            
            # Reset attempts count for this team after successful login
            attempts_df.loc[attempts_df['team_number'] == team_number, 'attempts'] = 0
            attempts_df.to_csv(attempts_file, index=False)
            
            return jsonify({'success': True})
        else:
            print(f"No match found for team={team_number}, passcode={passcode}")
            return jsonify({'success': False, 'message': 'Invalid credentials'})
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
# New Routes for CSV Management
# 1. Route to get all available CSVs
@app.route('/api/csv-files', methods=['GET'])
def get_csv_files():
    return jsonify({
        'files': [
            {'id': 'first-stage-credentials', 'name': 'First Stage Credentials'},
            {'id': 'second-stage-credentials', 'name': 'Second Stage Credentials'},
            {'id': 'first-stage-entries', 'name': 'First Stage Entries'},
            {'id': 'second-stage-entries', 'name': 'Second Stage Entries'}
        ]
    })

# 2. Route to get data from a specific CSV
@app.route('/api/csv/<csv_id>', methods=['GET'])
def get_csv_data(csv_id):
    if csv_id not in CSV_MAPPING:
        return jsonify({'error': 'CSV not found'}), 404
    
    try:
        df = pd.read_csv(CSV_MAPPING[csv_id])
        return jsonify({'data': df.to_dict(orient='records')})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 3. Route to add a new row to a CSV
@app.route('/api/csv/<csv_id>', methods=['POST'])
def add_csv_row(csv_id):
    if csv_id not in CSV_MAPPING:
        return jsonify({'error': 'CSV not found'}), 404
    
    try:
        data = request.json
        df = pd.read_csv(CSV_MAPPING[csv_id])
        
        # For entry CSVs, automatically add timestamp if not provided
        if csv_id in ['first-stage-entries', 'second-stage-entries'] and 'timestamp' not in data:
            data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        new_row = pd.DataFrame([data])
        df = pd.concat([df, new_row])
        df.to_csv(CSV_MAPPING[csv_id], index=False)
        
        return jsonify({'success': True, 'data': df.to_dict(orient='records')})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 4. Route to update a row in a CSV
@app.route('/api/csv/<csv_id>/<int:row_index>', methods=['PUT'])
def update_csv_row(csv_id, row_index):
    if csv_id not in CSV_MAPPING:
        return jsonify({'error': 'CSV not found'}), 404
    
    try:
        data = request.json
        df = pd.read_csv(CSV_MAPPING[csv_id])
        
        if row_index < 0 or row_index >= len(df):
            return jsonify({'error': 'Row index out of range'}), 400
        
        # Update the row
        for key, value in data.items():
            if key in df.columns:
                df.at[row_index, key] = value
        
        df.to_csv(CSV_MAPPING[csv_id], index=False)
        
        return jsonify({'success': True, 'data': df.to_dict(orient='records')})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 5. Route to delete a row from a CSV
@app.route('/api/csv/<csv_id>/<int:row_index>', methods=['DELETE'])
def delete_csv_row(csv_id, row_index):
    if csv_id not in CSV_MAPPING:
        return jsonify({'error': 'CSV not found'}), 404
    
    try:
        df = pd.read_csv(CSV_MAPPING[csv_id])
        
        if row_index < 0 or row_index >= len(df):
            return jsonify({'error': 'Row index out of range'}), 400
        
        # Delete the row
        df = df.drop(row_index).reset_index(drop=True)
        df.to_csv(CSV_MAPPING[csv_id], index=False)
        
        return jsonify({'success': True, 'data': df.to_dict(orient='records')})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 6. Route to get CSV schema (column names)
@app.route('/api/csv/<csv_id>/schema', methods=['GET'])
def get_csv_schema(csv_id):
    if csv_id not in CSV_MAPPING:
        return jsonify({'error': 'CSV not found'}), 404
    
    try:
        df = pd.read_csv(CSV_MAPPING[csv_id])
        return jsonify({'columns': list(df.columns)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  
    app.run(host="0.0.0.0", port=port)