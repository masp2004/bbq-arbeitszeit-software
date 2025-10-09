import sqlite3

conn = sqlite3.connect('system.db')
cursor = conn.cursor()
cursor.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            mitarbeiter_id INTEGER PRIMARY KEY,
            name VARCHAR(30) UNIQUE NOT NULL,
            password VARCHAR(15) NOT NULL,
            vertragliche_wochenstunden INTEGER NOT NULL,
            geburtsdatum DATE NOT NULL,   
            gleitzeit  DECIMAL(4,2) NOT NULL DEFAULT 0,
            letzter_login DATE NOT NULL
        );
        CREATE TABLE IF NOT EXISTS zeiteinträge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mitarbeiter_id INTEGER NOT NULL REFERENCES users(mitarbeiter_id),
                zeit TIME NOT NULL,
                datum DATE NOT NULL,
                validiert BOOLEAN  NOT NULL DEFAULT 0      
            ); 
        CREATE TABLE IF NOT EXISTS benachrichtigungen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mitarbeiter_id INTEGER NOT NULL REFERENCES users(mitarbeiter_id),
                benachrichtigungs_code INTEGER NOT NULL, 
                datum DATE    
            );         
                  
    ''')
conn.commit()
conn.close()
