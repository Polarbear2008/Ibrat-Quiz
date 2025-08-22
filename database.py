import sqlite3
from datetime import datetime

class Database:
    def _create_tables(self):
        """Create database tables if they don't exist"""
        # Create teams table first (referenced by other tables)
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS teams (
            team_id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_name TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create users table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            language TEXT,
            full_name TEXT,
            phone_number TEXT,
            english_level TEXT,
            age INTEGER,
            has_team BOOLEAN DEFAULT FALSE,
            team_id INTEGER,
            is_team_leader BOOLEAN DEFAULT FALSE,
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE SET NULL
        )
        ''')
        
        # Create team_members table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS team_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            phone_number TEXT NOT NULL,
            is_team_leader BOOLEAN DEFAULT FALSE,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            UNIQUE(team_id, user_id)
        )
        ''')
        self.connection.commit()
    
    def _update_schema(self):
        """Update database schema to the latest version"""
        try:
            # Enable foreign keys
            self.cursor.execute('PRAGMA foreign_keys = ON')
            
            # Check if users table has the required columns
            self.cursor.execute("PRAGMA table_info(users)")
            columns = [col[1] for col in self.cursor.fetchall()]
            
            # Add missing columns to users table
            if 'has_team' not in columns:
                self.cursor.execute('ALTER TABLE users ADD COLUMN has_team BOOLEAN DEFAULT FALSE')
            if 'is_team_leader' not in columns:
                self.cursor.execute('ALTER TABLE users ADD COLUMN is_team_leader BOOLEAN DEFAULT FALSE')
            if 'team_id' not in columns:
                self.cursor.execute('ALTER TABLE users ADD COLUMN team_id INTEGER')
            
            # Check if team_members table has the required columns
            self.cursor.execute("PRAGMA table_info(team_members)")
            team_members_columns = [col[1] for col in self.cursor.fetchall()]
            
            # Add missing columns to team_members table
            if 'is_team_leader' not in team_members_columns:
                self.cursor.execute('ALTER TABLE team_members ADD COLUMN is_team_leader BOOLEAN DEFAULT FALSE')
            if 'joined_at' not in team_members_columns:
                self.cursor.execute('ALTER TABLE team_members ADD COLUMN joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            
            self.connection.commit()
            
        except Exception as e:
            print(f"Error updating database schema: {e}")
            self.connection.rollback()
    
    def __init__(self, db_file='quiz_bot.db'):
        self.db_file = db_file
        self.connection = sqlite3.connect(db_file, check_same_thread=False)
        self.cursor = self.connection.cursor()
        
        # Create tables and update schema
        self._create_tables()
        self._update_schema()
        
        # Enable foreign key constraints
        self.cursor.execute('PRAGMA foreign_keys = ON')
        self.connection.commit()

    def user_exists(self, user_id):
        result = self.cursor.execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,))
        return result.fetchone() is not None

    def add_user(self, user_id, username='', first_name='', last_name=''):
        if not self.user_exists(user_id):
            self.cursor.execute('''
            INSERT INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name))
            self.connection.commit()

    def update_user_data(self, user_id, **data):
        set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
        values = list(data.values()) + [user_id]
        
        query = f"""
        UPDATE users 
        SET {set_clause}
        WHERE user_id = ?
        """
        self.cursor.execute(query, values)
        self.connection.commit()

    def get_user_data(self, user_id):
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        columns = [column[0] for column in self.cursor.description]
        user_data = self.cursor.fetchone()
        
        if user_data:
            user_dict = dict(zip(columns, user_data))
            # If user is in a team, get team info
            if user_dict.get('team_id'):
                user_dict['team'] = self.get_team_info(user_dict['team_id'])
                if user_dict['team']:
                    user_dict['team_members'] = self.get_team_members(user_dict['team_id'])
            return user_dict
        return None
        
    def create_team(self, team_name, leader_id, leader_name, leader_phone):
        try:
            # Start transaction
            self.connection.execute('BEGIN TRANSACTION')
            
            # Create team
            self.cursor.execute('''
            INSERT INTO teams (team_name) VALUES (?)
            ''', (team_name,))
            team_id = self.cursor.lastrowid
            
            # Update user as team leader
            self.cursor.execute('''
            UPDATE users 
            SET has_team = TRUE, team_id = ?, is_team_leader = TRUE 
            WHERE user_id = ?
            ''', (team_id, leader_id))
            
            # Add team leader as a team member
            self.cursor.execute('''
            INSERT INTO team_members (
                team_id, user_id, full_name, phone_number, is_team_leader, joined_at
            ) VALUES (?, ?, ?, ?, TRUE, CURRENT_TIMESTAMP)
            ''', (team_id, leader_id, leader_name, leader_phone))
            
            self.connection.commit()
            return team_id
            
        except sqlite3.IntegrityError as e:
            self.connection.rollback()
            if 'UNIQUE constraint failed: teams.team_name' in str(e):
                raise ValueError("A team with this name already exists.")
        except Exception as e:
            self.connection.rollback()
            raise
            
    def add_team_member(self, team_id, user_id, full_name, phone_number):
        try:
            # Start transaction
            self.connection.execute('BEGIN TRANSACTION')
            
            # Check if user is already in a team
            self.cursor.execute('SELECT team_id FROM users WHERE user_id = ?', (user_id,))
            result = self.cursor.fetchone()
            if result and result[0]:
                raise ValueError("This user is already in a team.")
            
            # Check if team exists and has less than 3 members (including leader)
            self.cursor.execute('''
            SELECT COUNT(*) FROM team_members WHERE team_id = ?
            ''', (team_id,))
            member_count = self.cursor.fetchone()[0]
            
            if member_count >= 3:  # Including leader
                raise ValueError("Team is already full (max 3 members including leader)")
            
            # Add team member
            self.cursor.execute('''
            INSERT INTO team_members (
                team_id, user_id, full_name, phone_number, is_team_leader, joined_at
            ) VALUES (?, ?, ?, ?, FALSE, CURRENT_TIMESTAMP)
            ''', (team_id, user_id, full_name, phone_number))
            
            # Update user's team status
            self.cursor.execute('''
            UPDATE users 
            SET has_team = TRUE, team_id = ?, is_team_leader = FALSE 
            WHERE user_id = ?
            ''', (team_id, user_id))
            
            self.connection.commit()
            return True, "Team member added successfully"
            
        except sqlite3.IntegrityError as e:
            self.connection.rollback()
            if 'UNIQUE constraint failed: team_members.team_id, team_members.user_id' in str(e):
                return False, "This user is already in this team."
            elif 'FOREIGN KEY constraint failed' in str(e):
                return False, "Team does not exist."
            else:
                return False, f"Database error: {str(e)}"
                
        except Exception as e:
            self.connection.rollback()
            return False, str(e)
            
    def get_team_info(self, team_id):
        # Get basic team info
        self.cursor.execute('''
        SELECT t.team_id, t.team_name, t.created_at,
               u.user_id as leader_id, u.full_name as leader_name, u.phone_number as leader_phone
        FROM teams t
        LEFT JOIN users u ON t.team_id = u.team_id AND u.is_team_leader = 1
        WHERE t.team_id = ?
        ''', (team_id,))
        
        team_data = self.cursor.fetchone()
        if not team_data:
            return None
            
        # Convert to dict
        columns = [column[0] for column in self.cursor.description]
        team_info = dict(zip(columns, team_data))
        
        # Add member count
        self.cursor.execute('''
        SELECT COUNT(*) FROM team_members WHERE team_id = ?
        ''', (team_id,))
        team_info['member_count'] = self.cursor.fetchone()[0]
        
        return team_info
        
    def get_team_members(self, team_id):
        self.cursor.execute('''
        SELECT user_id, full_name, phone_number, is_team_leader 
        FROM team_members 
        WHERE team_id = ?
        ORDER BY is_team_leader DESC, joined_at
        ''', (team_id,))
        columns = [column[0] for column in self.cursor.description]
        return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        
    def get_all_teams(self):
        """Get all teams with their members and leader information"""
        # Get all teams with their leader info
        self.cursor.execute('''
        SELECT t.team_id, t.team_name, t.created_at, 
               u.user_id as leader_id, u.full_name as leader_name, u.phone_number as leader_phone
        FROM teams t
        LEFT JOIN users u ON t.team_id = u.team_id AND u.is_team_leader = 1
        ORDER BY t.team_name
        ''')
        teams = self.cursor.fetchall()
        
        result = []
        for team in teams:
            team_id, team_name, created_at, leader_id, leader_name, leader_phone = team
            
            # Get all team members
            members = self.get_team_members(team_id)
            
            # Mark the team leader in the members list
            for member in members:
                if member['user_id'] == leader_id:
                    member['is_team_leader'] = True
                    break
            
            result.append({
                'team_id': team_id,
                'team_name': team_name,
                'created_at': created_at,
                'leader_id': leader_id,
                'leader_name': leader_name,
                'leader_phone': leader_phone,
                'members': members,
                'member_count': len(members)
            })
        
        return result
        
    def get_team_leaders(self):
        """Get all team leaders with their team info"""
        self.cursor.execute('''
        SELECT u.user_id, u.username, u.full_name, u.phone_number,
               t.team_id, t.team_name, t.created_at
        FROM users u
        JOIN teams t ON u.team_id = t.team_id
        WHERE u.is_team_leader = 1
        ORDER BY t.team_name
        ''')
        columns = [column[0] for column in self.cursor.description]
        return [dict(zip(columns, row)) for row in self.cursor.fetchall()]

    def get_all_users(self):
        self.cursor.execute('SELECT * FROM users')
        columns = [column[0] for column in self.cursor.description]
        return [dict(zip(columns, row)) for row in self.cursor.fetchall()]

    def export_to_csv(self, filename='users_export.csv'):
        """Export all user data to a CSV file"""
        import csv
        from datetime import datetime
        
        # Get all user data
        users = self.get_all_users()
        
        if not users:
            return False, "No users found in the database."
        
        # Define field names in a specific order
        fieldnames = [
            'user_id', 'username', 'first_name', 'last_name',
            'language', 'full_name', 'phone_number',
            'english_level', 'age', 'registration_date'
        ]
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for user in users:
                    writer.writerow(user)
            return True, f"Data exported successfully to {filename}"
        except Exception as e:
            return False, f"Error exporting to CSV: {str(e)}"

    def export_to_excel(self, filename='users_export.xlsx'):
        """Export all user data with team information to an Excel file"""
        try:
            import pandas as pd
            from pandas import ExcelWriter
            
            # Get all users and teams data
            users = self.get_all_users()
            teams = self.get_all_teams()
            
            if not users and not teams:
                return False, "No data found in the database."
            
            # Create a Pandas Excel writer using openpyxl as the engine
            with ExcelWriter(filename, engine='openpyxl') as writer:
                # Export users
                if users:
                    df_users = pd.DataFrame(users)
                    
                    # Format dates
                    date_columns = ['registration_date', 'created_at']
                    for col in date_columns:
                        if col in df_users.columns:
                            df_users[col] = pd.to_datetime(df_users[col]).dt.strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Reorder columns for better readability
                    columns_order = [
                        'user_id', 'username', 'first_name', 'last_name', 'full_name',
                        'language', 'phone_number', 'english_level', 'age',
                        'has_team', 'is_team_leader', 'team_id', 'registration_date'
                    ]
                    # Only include columns that exist in the DataFrame
                    columns_order = [col for col in columns_order if col in df_users.columns]
                    df_users = df_users[columns_order]
                    
                    df_users.to_excel(writer, sheet_name='Users', index=False)
                
                # Export teams
                if teams:
                    # Create teams data
                    teams_data = []
                    for team in teams:
                        for member in team['members']:
                            teams_data.append({
                                'team_id': team['team_id'],
                                'team_name': team['team_name'],
                                'created_at': team['created_at'],
                                'member_user_id': member.get('user_id'),
                                'member_name': member.get('full_name'),
                                'member_phone': member.get('phone_number'),
                                'is_team_leader': 1 if member.get('user_id') == team.get('leader_id') else 0
                            })
                    
                    if teams_data:
                        df_teams = pd.DataFrame(teams_data)
                        
                        # Format dates
                        if 'created_at' in df_teams.columns:
                            df_teams['created_at'] = pd.to_datetime(df_teams['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
                        
                        df_teams.to_excel(writer, sheet_name='Teams', index=False)
                
                # Auto-adjust columns' width
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    for column in worksheet.columns:
                        max_length = 0
                        column = [cell for cell in column]
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = (max_length + 2)
                        worksheet.column_dimensions[column[0].column_letter].width = min(adjusted_width, 50)
            
            return True, f"Data exported successfully to {filename}"
            
        except ImportError as e:
            return False, "Please install required packages: pandas and openpyxl (pip install pandas openpyxl)"
        except Exception as e:
            return False, f"Error exporting to Excel: {str(e)}"

    def close(self):
        """Close the database connection"""
        self.connection.close()
