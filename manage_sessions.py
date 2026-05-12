import json
import os
import sys

SESSION_FILE = "session_strings.json"


def load_sessions():
    if not os.path.exists(SESSION_FILE):
        return {}
    try:
        with open(SESSION_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def save_sessions(data):
    with open(SESSION_FILE, "w") as f:
        json.dump(data, f, indent=2)


def main():
    print("=== TELEGRAM WORKER MANAGER ===")
    print("Use this tool to add worker accounts since Admin Panel is removed.")

    while True:
        data = load_sessions()
        print(f"\nActive Workers: {len(data)}")
        print("1. Add New Session String")
        print("2. List Workers")
        print("3. Remove Worker")
        print("4. Exit")

        choice = input("Choice: ")

        if choice == "1":
            phone = input("Phone Number (e.g., +1202...): ")
            string = input("Pyrogram Session String: ").strip()
            if len(string) < 10:
                print("ERROR: Invalid string length!")
                continue
            data[phone] = string
            save_sessions(data)
            print("✅ Added!")

        elif choice == "2":
            for i, (ph, st) in enumerate(data.items(), 1):
                print(f"{i}. {ph} -> {st[:15]}...")

        elif choice == "3":
            phone = input("Phone Number to delete: ")
            if phone in data:
                del data[phone]
                save_sessions(data)
                print("🗑️ Deleted.")
            else:
                print("Not found.")

        elif choice == "4":
            break


if __name__ == "__main__":
    main()
