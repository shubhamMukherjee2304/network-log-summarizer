import sqlite3
import re
import os

#configureation

LOG_FILE = 'logs/network_logs.log'
DB_FILE = 'logs/logs.db'

#regex to match the format in the logs

LOG_PATTERN = re.compile(
    #extracting timestamp
    r'(?P<timestamp>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+'
    #extracting device
    r'(?P<device>\S+)\s+'
    #extracting security
    r'(?:%\S+-\d-)?(?P<severity>[A-Z0-9]+):\s+'
    #extracting messages
    r'(?P<message>.*)'
)

def parse_log_line(line):
    """Parse a single log line using the defined regex"""
    match = LOG_PATTERN.match(line)
    if match:
        #returning a dictionary
        return match.groupdict()
    return None


#main execution function
def parse_and_store_logs():
    """Coordinates the parsing of log files and its insertion in the database."""
    conn = sqlite3.connect(DB_FILE)
    create_db_and_table(conn)
    logs_processed = 0
    #read and parse log file
    try:
        with open(LOG_FILE, 'r') as f:
            for line in f:
                parsed_data = parse_log_line(line.strip())
                if parsed_data:
                    insert_log_entry(conn, parsed_data)
                    logs_processed +=1
    except FileNotFoundError:
        print(f"Error: File not foud at {LOG_FILE}")
        return

    conn.close()
    print(f"Successfully populated '{DB_FILE}' with '{logs_processed}' structured log entries")


def create_db_and_table(conn):
    """Creates the SQlite table Schema"""
    cursor = conn.cursor()
    #The SQL cmd
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    device TEXT,
    severity TEXT,
    message TEXT
    );
    """)

    conn.commit()
    print("Database table 'logs' ensured")

def insert_log_entry(conn, entry):
        """Inserts a single parsed log entry into the db"""
        cursor = conn.cursor()
        #'?'(placeholders) to prevent sql injections
        cursor.execute("""
        INSERT INTO logs (timestamp, device, severity, message) VALUES (?,?,?,?)
        """, (entry['timestamp'], entry['device'], entry['severity'], entry['message']))

        conn.commit()

#entry point
if __name__ == '__main__':
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print(f"Removed old databse: {DB_FILE}")
        parse_and_store_logs()
