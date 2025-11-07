SELECT * FROM users
SELECT * FROM zeiteinträge
SELECT * FROM benachrichtigungen

INSERT INTO zeiteinträge (mitarbeiter_id, zeit, datum, validiert)
VALUES (1, '07:00:00', '2025-10-03', 0);

INSERT INTO zeiteinträge (mitarbeiter_id, zeit, datum, validiert)
VALUES (1, '16:30:00', '2025-10-02', 0);


UPDATE users
SET letzter_login = '2025-10-01'
WHERE mitarbeiter_id = 1;


DELETE FROM zeiteinträge
WHERE mitarbeiter_id = 1
  AND zeit = '07:00:00'
  AND datum = '2025-10-02';

UPDATE zeiteinträge
SET validiert = 0;



UPDATE users
SET gleitzeit = 0
WHERE mitarbeiter_id = 1;