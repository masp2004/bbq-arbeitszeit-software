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
            letzter_login DATE NOT NULL,
            ampel_grün INTEGER NOT NULL DEFAULT 5,
            ampel_rot INTEGER NOT NULL DEFAULT -5,
            vorgesetzter_id INTEGER   REFERENCES users(mitarbeiter_id)
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
                datum DATE,
                ist_popup BOOLEAN NOT NULL DEFAULT 0,
                popup_uhrzeit TIME
            );
        CREATE TABLE IF NOT EXISTS abwesenheiten (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mitarbeiter_id INTEGER NOT NULL REFERENCES users(mitarbeiter_id),
                datum DATE NOT NULL,
                typ TEXT CHECK (typ IN ('Urlaub', 'Krankheit', 'Fortbildung', 'Sonstiges')) NOT NULL,
                genehmigt BOOLEAN NOT NULL DEFAULT 0
            );
        CREATE TABLE IF NOT EXISTS wochenstunden_historie (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mitarbeiter_id INTEGER NOT NULL REFERENCES users(mitarbeiter_id),
                gueltig_ab DATE NOT NULL,
                wochenstunden INTEGER NOT NULL,
                UNIQUE (mitarbeiter_id, gueltig_ab)
            );         
                  
    ''')
conn.commit()
conn.close()