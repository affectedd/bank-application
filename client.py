import socket
import sys

HOST = '127.0.0.1'
PORT = 65432

def send_command(sock, command_str):
    sock.sendall(command_str.encode('utf-8'))
    return sock.recv(1024).decode('utf-8')


def admin_menu(sock):
    while True:
        print("\n--- ADMINISTRATOR MENU ---")
        print("1. View all accounts")
        print("2. Edit a user account")
        print("3. Delete a user account")
        print("4. Exit")

        choice = input("Enter the option: ").strip()

        if choice == "1":
            response = send_command(sock, "ADMIN_GET_USERS")
            print("\n=== LIST OF USERS ===")
            print(response.replace("ADMIN_USERS_DATA\n",""))

        elif choice == "2":
            target_user = input("Enter the username to edit: ").strip()

            if not target_user:
                print("\n[ERROR] Username cannot be empty.")
                continue

            new_username = input("Enter the new username: ").strip()
            if not new_username:
                print("\n[ERROR] New username cannot be empty.")
                continue


            response = send_command(sock, f"ADMIN_EDIT_USER {target_user} {new_username}")

            if response == "SUCCESS_USER_UPDATED":
                print(f"\n[SUCCESS] Username for '{target_user}' changed to '{new_username}'.")
            elif response == "ERROR_FORBIDDEN":
                print("\n[ERROR] You do not have admin privileges.")
            elif response == "ERROR_USER_NOT_FOUND":
                print(f"\n[ERROR] User '{target_user}' not found.")
            elif response == "ERROR_CANNOT_EDIT_ADMIN":
                print("\n[ERROR] You cannot edit the admin account.")
            elif response == "ERROR_DATABASE_FAILED":
                print("\n[ERROR] Database error. Maybe this username is already taken?")
            else:
                print(f"\n[ERROR] Unknown server response: {response}")

        elif choice == "3":
            target_user = input("Enter the username to delete: ").strip()

            if not target_user:
                print("\n[ERROR] Username cannot be empty.")
                continue

            response = send_command(sock, f"ADMIN_DELETE_USER {target_user}")

            if response == "DELETE_SUCCESS":
                print(f"\n[SUCCESS] User '{target_user}' has been deleted successfully!")
            elif response == "ERROR_USER_NOT_FOUND":
                print("\n[ERROR] This user does not exist.")
            elif response == "ERROR_CANNOT_DELETE_ADMIN":
                print("[ERROR] Critical error: You cannot delete the admin account!")
            elif response == "ERROR_FORBIDDEN":
                print("\n[ERROR] Access denied. You don't have enough permissions to delete the account.")
            else:
                print(f"\n[ERROR] Failed to delete user: {response}")

        elif choice == "4":
            print("\nAdmin logged out.")
            break
        else:
            print("Invalid option.")

def bank_menu(sock):
    while True:
        print("\n--- Client Panel ---")
        print("1. Check your account balance")
        print("2. Make a transfer")
        print("3. View transaction history")
        print("4. View notifications")
        print("5. Exit")

        choice = input("Enter the option: ").strip()

        if choice == "1":
            response = send_command(sock, "BALANCE")
            if response.startswith("BALANCE:"):
                balance = response.split()[1]
                print(f"\n[BALANCE] Current account balance: {balance} USD")
            else:
                print(f"\n[ERROR] Failed to get balance: {response}")

        elif choice == "2":
            recipient = input("Enter the recipient username: ").strip()
            amount = input("Enter the amount to transfer: ").strip()
            description = input("Enter the description of the transfer(optional): ").strip()

            description_safe = description.replace(" ", "_") if description else "Transfer"

            command = f"TRANSFER {recipient} {amount} {description_safe}"
            response = send_command(sock, command)

            if response == "TRANSFER_SUCCESS":
                print("\n[SUCCESS] The transfer has been completed successfully!")
            elif response == "ERROR_RECIPIENT_NOT_FOUND":
                print("\n[ERROR] Recipient doesn't exist.")
            elif response == "ERROR_NOT_ENOUGH_BALANCE":
                print("\n[ERROR] You don't have enough balance to transfer.")
            elif response == "ERROR_CANNOT_TRANSFER_TO_YOURSELF":
                print("\n[ERROR] You cannot transfer to yourself.")
            else:
                print(f"\n[ERROR] Failed to transfer: {response}")


        elif choice == "3":
            response = send_command(sock, "HISTORY")
            print("\n=== TRANSACTION HISTORY ===")
            if response == "HISTORY_EMPTY":
                print("No transactions found.")
            else:
                print(response.replace("HISTORY_DATA\n",""))

        elif choice == "4":
            response = send_command(sock, "NOTIFICATIONS")
            print("\n=== YOUR NOTIFICATIONS ===")
            if response == "NOTIFICATIONS_EMPTY":
                print("No new notifications.")
            else:
                print(response.replace("NOTIFICATIONS_DATA\n",""))
        elif choice == "5":
            print("\nLogged out.")
            break
        else:
            print("\nInvalid option.")

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((HOST, PORT))
    except ConnectionRefusedError:
        print("[ERROR] Failed to connect.")
        return

    print("=== WELCOME TO BANK ===")

    while True:
        print("\n1. Login")
        print("2. Register")
        print("3. Close")

        choice = input("Choose the option: ").strip()

        if choice == "1":
            username = input("Enter the login: ").strip()
            password = input("Enter the password: ").strip()

            response = send_command(sock, f"LOGIN {username} {password}")

            if response == "LOGIN_SUCCESS":
                print(f"\n[SUCCESS] Hello {username}!")
                if username == "admin":
                    admin_menu(sock)
                else:
                    bank_menu(sock)
            else:
                print("\n[ERROR] Invalid login or password.")

        elif choice == "2":
            username = input("Enter the login: ").strip()
            password = input("Enter the password: ").strip()

            response = send_command(sock, f"REGISTER {username} {password}")

            if response == "REGISTER_SUCCESS":
                print(f"\n[SUCCESS] The account has been created! Now you can login.")
            elif response == "ERROR_USER_EXISTS":
                print(f"\n[ERROR] A user with this login already exists.")
            else:
                print(f"\n[ERROR] Registration failed: {response}")

        elif choice == "3":
            print("Thank you for using our services.")
            sock.close()
            sys.exit()
        else:
            print("Invalid option.")

if __name__ == "__main__":
    main()
