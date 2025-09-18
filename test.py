import random
import datetime

# Zufälliges Hallo
greetings = ["Moin", "Servus", "Hey", "Na", "Hallo"]
print(random.choice(greetings), "👋")

# Kleine Spielerei mit Zufallszahlen
zahlen = [random.randint(1, 100) for _ in range(5)]
print("Zufallszahlen:", zahlen)

# Datum & Uhrzeit
jetzt = datetime.datetime.now()
print("Aktuelles Datum:", jetzt.strftime("%d.%m.%Y %H:%M:%S"))

# Mini-Funktion
def würfel():
    return random.randint(1, 6)

print("Würfelwurf:", würfel())