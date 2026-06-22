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
            print("\n=== LIST OF USERS & ACCOUNTS ===")
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
        print("5. Create shared account")
        print("6. Leave a shared account")
        print("7. Delete my profile/account")
        print("8. Exit")

        choice = input("Enter the option: ").strip()

        if choice == "1":
            response = send_command(sock, "BALANCE")
            print("\n=== YOUR ACCOUNTS ===")
            if response == "BALANCE_EMPTY":
                print("You don't have any accounts active.")
            elif response.startswith("BALANCE_DATA\n"):
                print(response.replace("BALANCE_DATA\n", ""))
            else:
                print(f"[ERROR] Failed to get balance: {response}")

        elif choice == "2":
            print("\n--- MAKE A TRANSFER ---")
            source_acc = input("Enter YOUR account number to transfer FROM: ").strip()
            recipient_acc = input("Enter RECIPIENT account number to transfer TO: ").strip()
            amount = input("Enter the amount to transfer: ").strip()
            description = input("Enter the description of the transfer (optional): ").strip()

            if not source_acc or not recipient_acc or not amount:
                print("\n[ERROR] Required fields cannot be empty.")
                continue

            description_safe = description.replace(" ", "_") if description else "Transfer"
            command = f"TRANSFER {source_acc} {recipient_acc} {amount} {description_safe}"
            response = send_command(sock, command)

            if response == "TRANSFER_SUCCESS":
                print("\n[SUCCESS] The transfer has been completed successfully!")
            elif response == "ERROR_SOURCE_ACCOUNT_NOT_FOUND":
                print("\n[ERROR] Source account not found or it doesn't belong to you.")
            elif response == "ERROR_RECIPIENT_NOT_FOUND":
                print("\n[ERROR] Recipient account doesn't exist.")
            elif response == "ERROR_NOT_ENOUGH_BALANCE":
                print("\n[ERROR] You don't have enough balance on this account.")
            elif response == "ERROR_CANNOT_TRANSFER_TO_YOURSELF":
                print("\n[ERROR] You cannot transfer to the same account.")
            elif response == "ERROR_INVALID_AMOUNT" or response == "ERROR_BAD_ARGUMENTS":
                print("\n[ERROR] Invalid transfer amount or arguments.")
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
            partner = input("Enter the username of your partner (husband/wife): ").strip()
            if not partner:
                print("\n[ERROR] Partner username cannot be empty.")
                continue

            partner_pesel = input("Enter the PESEL of your partner (11 digits): ").strip()
            if not partner_pesel.isdigit() or len(partner_pesel) != 11:
                print("\n[ERROR] Invalid partner PESEL format! It must be exactly 11 digits.")
                continue

            response = send_command(sock, f"CREATE_SHARED_ACCOUNT {partner} {partner_pesel}")

            if response.startswith("SHARED_SUCCESS"):
                acc_num = response.split()[1]
                print(f"\n[SUCCESS] Shared account {acc_num} has been successfully created with {partner}!")
            elif response == "ERROR_PARTNER_NOT_FOUND":
                print("\n[ERROR] This user does not exist.")
            elif response == "ERROR_CANNOT_SHARE_WITH_YOURSELF":
                print("\n[ERROR] You cannot create a shared account with yourself.")
            else:
                print(f"\n[ERROR] Failed: {response}")

        elif choice == "6":
            print("\n--- LEAVE A SHARED ACCOUNT ---")
            acc_num = input("Enter the shared account number you want to leave: ").strip()
            if not acc_num:
                print("\n[ERROR] Account number cannot be empty.")
                continue

            response = send_command(sock, f"LEAVE_SHARED_ACCOUNT {acc_num}")

            if response == "LEAVE_SHARED_ACCOUNT_SUCCESS":
                print(f"\n[SUCCESS] You have successfully left the shared account {acc_num}!")
            elif response == "ERROR_ACCOUNT_NOT_FOUND":
                print("\n[ERROR] Account not found or it doesn't belong to you.")
            elif response == "ERROR_CANNOT_LEAVE_PERSONAL_ACCOUNT":
                print(
                    "\n[ERROR] You cannot leave your personal account. You can only close/delete your entire profile.")
            else:
                print(f"\n[ERROR] Failed to leave account: {response}")

        elif choice == "7":
            print("\nWARNING: This will permanently delete your profile and all your personal accounts!")
            confirm = input("Are you absolutely sure? Type 'YES' to confirm: ").strip()

            if confirm == "YES":
                response = send_command(sock, "DELETE_MY_ACCOUNT")
                if response == "DELETE_PROFILE_SUCCESS":
                    print("\n[SUCCESS] Your profile has been successfully deleted. Goodbye!")
                    break
                elif response == "ERROR_CANNOT_DELETE_ADMIN":
                    print("\n[ERROR] You cannot delete the admin account via client menu.")
                else:
                    print(f"\n[ERROR] Failed to delete profile: {response}")
            else:
                print("\nDeletion cancelled.")

        elif choice == "8":
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
            pesel = input("Enter your PESEL (11 digits): ").strip()

            if not username or not password or not pesel:
                print("\n[ERROR] All fields are required.")
                continue

            response = send_command(sock, f"LOGIN {username} {password} {pesel}")

            if response == "LOGIN_SUCCESS":
                print(f"\n[SUCCESS] Hello {username}!")
                if username == "admin":
                    admin_menu(sock)
                else:
                    bank_menu(sock)
            else:
                print("\n[ERROR] Invalid login, password or PESEL.")

        elif choice == "2":
            username = input("Enter the login: ").strip()
            password = input("Enter the password: ").strip()
            pesel = input("Enter your PESEL (11 digits): ").strip()

            if not pesel.isdigit() or len(pesel) != 11:
                print("\n[ERROR] Invalid PESEL format! It must be exactly 11 digits.")
                continue

            response = send_command(sock, f"REGISTER {username} {password} {pesel}")

            if response == "REGISTER_SUCCESS":
                print(f"\n[SUCCESS] The account has been created! Now you can login.")
            elif response == "ERROR_USER_EXISTS":
                print(f"\n[ERROR] A user with this login already exists.")
            elif response == "ERROR_PESEL_EXISTS":
                print(f"\n[ERROR] A user with this PESEL already exists in the system.")
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
