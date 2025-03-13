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
    
    # Initialize attempts tracking CSV
    attempts_file = 'attempts_tracking.csv'
    if not os.path.exists(attempts_file):
        pd.DataFrame(columns=['team_number', 'attempts']).to_csv(attempts_file, index=False)
    
    # Initialize first stage entries CSV with original structure
    if not os.path.exists(FIRST_STAGE_ENTRIES_CSV):
        pd.DataFrame(columns=['team_number', 'timestamp']).to_csv(FIRST_STAGE_ENTRIES_CSV, index=False)
    
    # Initialize second stage entries CSV with updated structure including attempts and entry number
    if not os.path.exists(SECOND_STAGE_ENTRIES_CSV):
        pd.DataFrame(columns=['team_number', 'timestamp', 'attempts', 'entry_number']).to_csv(SECOND_STAGE_ENTRIES_CSV, index=False)
    else:
        # Update existing second stage entries CSV to include attempts and entry_number columns
        try:
            df = pd.read_csv(SECOND_STAGE_ENTRIES_CSV)
            
            # Add attempts column if it doesn't exist
            if 'attempts' not in df.columns:
                df['attempts'] = 0  # Initialize with zero for existing entries
            
            # Add entry_number column if it doesn't exist
            if 'entry_number' not in df.columns:
                # Calculate entry numbers for each team
                entry_numbers = []
                for idx, row in df.iterrows():
                    team = row['team_number']
                    # Count entries for this team up to this point (inclusive)
                    count = len(df.loc[:idx][df.loc[:idx]['team_number'] == team])
                    entry_numbers.append(count)
                
                df['entry_number'] = entry_numbers
            
            df.to_csv(SECOND_STAGE_ENTRIES_CSV, index=False)
        except Exception as e:
            print(f"Error updating existing entries CSV: {str(e)}")
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
        
        # Determine which credentials to check based on odd/even team number
        try:
            numeric_team = int(team_number)
            # If team number is odd, use team 1 credentials; if even, use team 2 credentials
            csv_team_to_check = "1" if numeric_team % 2 == 1 else "2"
        except ValueError:
            # If team number can't be converted to int, default to team 1
            csv_team_to_check = "1"
            
        print(f"Team number {team_number} is {'odd' if csv_team_to_check == '1' else 'even'}, checking against team {csv_team_to_check}")
        
        # Get the credentials for the determined team
        team_creds = df[df['team_number'] == csv_team_to_check]
        
        if not team_creds.empty:
            expected_passcode = team_creds.iloc[0]['passcode']
            
            # Verify credentials against the selected team's passcode
            if passcode == expected_passcode:
                # Record successful entry in csv3
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                entry_df = pd.read_csv(FIRST_STAGE_ENTRIES_CSV)
                new_entry = pd.DataFrame([{'team_number': team_number, 'timestamp': timestamp}])
                entry_df = pd.concat([entry_df, new_entry])
                entry_df.to_csv(FIRST_STAGE_ENTRIES_CSV, index=False)
                
                return jsonify({'success': True})
            else:
                print(f"Password mismatch for team {team_number} (checking against team {csv_team_to_check})")
                return jsonify({'success': False, 'message': 'Invalid credentials'})
        else:
            print(f"Team {csv_team_to_check} not found in credentials file")
            return jsonify({'success': False, 'message': 'Configuration error'})
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
        
        # Determine which credentials to check based on odd/even team number
        try:
            numeric_team = int(team_number)
            # If team number is odd, use team 1 credentials; if even, use team 2 credentials
            csv_team_to_check = "1" if numeric_team % 2 == 1 else "2"
        except ValueError:
            # If team number can't be converted to int, default to team 1
            csv_team_to_check = "1"
            
        print(f"Team number {team_number} is {'odd' if csv_team_to_check == '1' else 'even'}, checking against team {csv_team_to_check}")
        
        # Get the credentials for the determined team
        team_creds = df[df['team_number'] == csv_team_to_check]
        
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
        
        if not team_creds.empty:
            expected_passcode = team_creds.iloc[0]['passcode']
            
            # Verify credentials against the selected team's passcode
            if passcode == expected_passcode:
                # Load entry data
                entry_df = pd.read_csv(SECOND_STAGE_ENTRIES_CSV)
                
                # Calculate entry count for this team
                team_entries = len(entry_df[entry_df['team_number'] == team_number]) + 1  # +1 for current entry
                
                # Record successful entry with attempts count and entry number
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Add attempts data to the entry
                new_entry = pd.DataFrame([{
                    'team_number': team_number, 
                    'timestamp': timestamp,
                    'attempts': current_attempts,
                    'entry_number': team_entries
                }])
                
                entry_df = pd.concat([entry_df, new_entry])
                entry_df.to_csv(SECOND_STAGE_ENTRIES_CSV, index=False)
                
                # Reset attempts count for this team after successful login
                attempts_df.loc[attempts_df['team_number'] == team_number, 'attempts'] = 0
                attempts_df.to_csv(attempts_file, index=False)
                
                return jsonify({'success': True})
            else:
                print(f"Password mismatch for team {team_number} (checking against team {csv_team_to_check})")
                return jsonify({'success': False, 'message': 'Invalid credentials'})
        else:
            print(f"Team {csv_team_to_check} not found in credentials file")
            return jsonify({'success': False, 'message': 'Configuration error'})
    
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