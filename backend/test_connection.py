import sys
import psycopg2

passwords = ["postgres", "admin", "root", "123456", "password", ""]
success = False

for pwd in passwords:
    try:
        conn = psycopg2.connect(
            host="localhost",
            user="postgres",
            password=pwd,
            port=9571,
            connect_timeout=3
        )
        print(f"CONNECTION SUCCESS! User: postgres, Password: '{pwd}'")
        conn.close()
        success = True
        break
    except Exception as e:
        print(f"Failed with password '{pwd}': {e}")

if not success:
    print("Could not connect with default passwords. Please specify the connection password.")
    sys.exit(1)
else:
    sys.exit(0)
