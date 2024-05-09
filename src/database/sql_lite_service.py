from abc import ABC
import sqlite3

class SqlLiteService(ABC):
    def __init__(self, database_name = "Question-Generator-Evaluator-Tool"):
        print("database initialized")
        self.database_name = database_name + ".db"
        self.connection = sqlite3.connect(self.database_name, check_same_thread=False)
        
        self.initialize_database()
        
    def close_connection(self):
        self.connection.close()
              
    def initialize_database(self):

        cursor = self.connection.cursor()

        # Create 'user' table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user (
            user_name TEXT PRIMARY KEY
        )
        ''')

        # Create 'document' table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS document (
            document_name TEXT,
            sections_number INTEGER,
            PRIMARY KEY (document_name, sections_number)
        )
        ''')

        # Create 'rating' table
        # Note: The rating table combines user_name, document_name, and page_number as a composite key to ensure uniqueness.
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS rating (
            user_name TEXT,
            document_name TEXT,
            section_number INTEGER,
            rating INTEGER,
            generated_question TEXT,
            ai_model TEXT,
            FOREIGN KEY (user_name) REFERENCES user(user_name),
            FOREIGN KEY (document_name) REFERENCES document(document_name),
            PRIMARY KEY (user_name, document_name, section_number, ai_model)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS response (
            user_name TEXT,
            document_name TEXT,
            section_number INTEGER,
            ai_model TEXT,
            generated_model TEXT,
            rating INTEGER,
            generated_response TEXT,
            generation_type Text,
            FOREIGN KEY (user_name) REFERENCES user(user_name),
            FOREIGN KEY (document_name) REFERENCES document(document_name),
            FOREIGN KEY (section_number) REFERENCES rating(section_number),
            FOREIGN KEY (section_number) REFERENCES rating(ai_model),
            PRIMARY KEY (user_name, document_name, section_number, ai_model, generated_model, generation_type)
        )
        ''')

        # Commit changes and close the connection
        self.connection.commit()
        
    def check_if_user_exists(self, user_name):
        cursor = self.connection.cursor()
        cursor.execute('''
            SELECT * FROM user
            WHERE user_name = ?
        ''', (user_name,))
        
        result = cursor.fetchone()
        if result:
            return True
        return False
        
    def add_user(self, user_name):
        if not self.check_if_user_exists(user_name):
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT INTO user (user_name)
                VALUES (?)
            ''', (user_name,))
            self.connection.commit()
           
    def check_if_document_exists(self, document_name):
        cursor = self.connection.cursor()
        cursor.execute('''
            SELECT * FROM document
            WHERE document_name = ?
        ''', (document_name,))
        
        result = cursor.fetchone()
        if result:
            return True
        return False
     
    def add_document(self, document_name, sections_number):
        if not self.check_if_document_exists(document_name):
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT INTO document (document_name, sections_number)
                VALUES (?, ?)
            ''', (document_name, sections_number))
            self.connection.commit()
        
    def add_rating(self, user_name, document_name, section_number, rating, generated_question, ai_model):
        cursor = self.connection.cursor()
        cursor.execute('''
            INSERT INTO rating (user_name, document_name, section_number, rating, generated_question, ai_model)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_name, document_name, section_number, rating, generated_question, ai_model))
        self.connection.commit()
        
    def add_response(self, user_name, document_name, section_number, ai_model, generated_response, generated_model, generation_type, rating):
        cursor = self.connection.cursor()
        cursor.execute('''
            INSERT INTO response (user_name, document_name, section_number, ai_model, generated_response, generated_model, generation_type, rating)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_name, document_name, section_number, ai_model, generated_response, generated_model, generation_type, rating))
        self.connection.commit()
        
    def get_ratings(self, user_name, document_name):
        cursor = self.connection.cursor()
        cursor.execute('''
            SELECT section_number, rating, generated_question, ai_model FROM rating
            WHERE user_name = ? AND document_name = ?
        ''', (user_name, document_name))
        return cursor.fetchall()
    
    def get_responses(self, user_name, document_name):
        cursor = self.connection.cursor()
        cursor.execute('''
            SELECT * FROM response
            WHERE user_name = ? AND document_name = ?
        ''', (user_name, document_name))
        return cursor.fetchall()
        
    def get_all_ratings(self):
        cursor = self.connection.cursor()
        cursor.execute('''
            SELECT * FROM rating
        ''')
        return cursor.fetchall()
        
    def check_for_rating(self, user_name, document_name, section_number):
        # Connect to the SQLite database
        
        cursor = self.connection.cursor()

        # Check if there is already a rating for the given user, document, and page
        cursor.execute('''
            SELECT rating FROM rating
            WHERE user_name = ? AND document_name = ? AND section_number = ?
        ''', (user_name, document_name, section_number))
        
        result = cursor.fetchone()

        if result:
            # A rating exists, display it
            print(f"User '{user_name}' has already rated document '{document_name}', page {section_number}, with a rating of {result[0]}.")
       
    def update_rating(self, user_name, document_name, section_number, rating, generated_question, ai_model):
        cursor = self.connection.cursor()

        # Check if the rating already exists
        cursor.execute('''
            SELECT rating FROM rating
            WHERE user_name = ? AND document_name = ? AND section_number = ? AND ai_model = ?
        ''', (user_name, document_name, section_number, ai_model))
        
        result = cursor.fetchone()

        if result:
            # Update the existing rating
            cursor.execute('''
                UPDATE rating
                SET rating = ?
                WHERE user_name = ? AND document_name = ? AND section_number = ? AND ai_model = ?
            ''', (rating, user_name, document_name, section_number, ai_model))
            print(f"Rating updated for user '{user_name}' on document '{document_name}', page {section_number} to {rating}.")
        else:
            self.add_rating(user_name, document_name, section_number, rating, generated_question, ai_model)
            
    def update_response(self, user_name, document_name, section_number, ai_model, generated_response, generated_model, generation_type, rating):
        cursor = self.connection.cursor()
        
        # Check if the rating already exists
        cursor.execute('''
            SELECT rating FROM response
            WHERE user_name = ? AND document_name = ? AND section_number = ? AND ai_model = ? AND generated_model = ? AND generation_type = ?
        ''', (user_name, document_name, section_number, ai_model, generated_model, generation_type))
        
        result = cursor.fetchone()

        if result:
            # Update the existing rating
            cursor.execute('''
                UPDATE response
                SET rating = ?
                WHERE user_name = ? AND document_name = ? AND section_number = ? AND ai_model = ? AND generated_model = ? AND generation_type = ?
            ''', (rating, user_name, document_name, section_number, ai_model, generated_model, generation_type))
            print(f"Rating updated for user '{user_name}' on document '{document_name}', page {section_number} to {rating}.")
        else:
            self.add_response(user_name, document_name, section_number, ai_model, generated_response, generated_model, generation_type, rating)
 
        self.connection.commit()

            
