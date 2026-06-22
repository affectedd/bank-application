import socket
import threading
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.auth import verify_password, get_password_hash
from app import models
from sqlalchemy import or_
import random

models.Base.metadata.create_all(bind=engine)
HOST = '127.0.0.1'
PORT = 65432

def generate_acoount_number(db: Session):
    while True:
        num = "".join([str(random.randint(0, 9)) for _ in range(16)])
        exists = db.query(models.Account).filter(models.Account.account_number == num).first()
        if not exists:
            return num

def handle_client(conn, addr):
    print(f"[New Connection] {addr} connected.")
    db: Session = SessionLocal()
    current_user = None

    try:
        while True:
            data = conn.recv(1024).decode('utf-8')
            if not data:
                break

            parts = data.strip().split(maxsplit=4)
            if not parts:
                continue

            command = parts[0].upper()

            if command == "REGISTER":
                if len(parts) < 4:
                    conn.sendall(b"ERROR_BAD_ARGUMENTS")
                    continue
                username, password, pesel = parts[1], parts[2], parts[3]
                existing_user = db.query(models.User).filter(models.User.username == username).first()
                existing_pesel = db.query(models.User).filter(models.User.pesel == pesel).first()

                if existing_user:
                    conn.sendall(b"ERROR_USER_EXISTS")
                    continue
                elif existing_pesel:
                    conn.sendall(b"ERROR_PESEL_EXISTS")
                    continue
                else:
                    hashed=get_password_hash(password)
                    new_user = models.User(username=username, hashed_password=hashed, pesel=pesel)
                    acc_num = generate_acoount_number(db)
                    new_account = models.Account(account_number=acc_num, balance=1000.0)
                    new_user.accounts.append(new_account)
                    db.add(new_user)
                    db.add(new_account)
                    db.commit()
                    conn.sendall(b"REGISTER_SUCCESS")



            elif command == "LOGIN":
                if len(parts) < 4:
                    conn.sendall(b"ERROR_BAD_ARGUMENTS")
                    continue
                username, password, pesel= parts[1], parts[2], parts[3]
                user = db.query(models.User).filter(models.User.username == username).first()
                if user and verify_password(password, user.hashed_password) and user.pesel == pesel:
                    current_user = user
                    conn.sendall(b"LOGIN_SUCCESS")
                else:
                    conn.sendall(b"LOGIN_FAILED")
            elif not current_user:
                conn.sendall(b"ERROR_UNAUTHORIZED")

            elif command == "CREATE_SHARED_ACCOUNT":
                if len(parts) < 3:
                    conn.sendall(b"ERROR_BAD_ARGUMENTS")
                    continue
                partner_username, partner_pesel = parts[1], parts[2]

                if partner_username == current_user.username:
                    conn.sendall(b"ERROR_CANNOT_SHARE_WITH_YOURSELF")
                    continue

                partner = db.query(models.User).filter(
                    models.User.username == partner_username,
                    models.User.pesel == partner_pesel
                ).first()

                if not partner:
                    conn.sendall(b"ERROR_PARTNER_NOT_FOUND")
                    continue

                try:
                    acc_num = generate_acoount_number(db)
                    shared_account = models.Account(account_number=acc_num, balance=0.0)

                    current_user.accounts.append(shared_account)
                    partner.accounts.append(shared_account)

                    new_notification = models.Notification(
                        user_id=partner.id,
                        message=f"User {current_user.username} created a SHARED ACCOUNT ({acc_num}) with you!"
                    )
                    db.add(new_notification)
                    db.add(shared_account)
                    db.commit()

                    conn.sendall(f"SHARED_SUCCESS {acc_num}".encode('utf-8'))
                except Exception as e:
                    db.rollback()
                    conn.sendall(b"ERROR_FAILED_TO_CREATE")


            elif command == "BALANCE":
                db.refresh(current_user)
                if not current_user.accounts:
                    conn.sendall(b"BALANCE_EMPTY")
                    continue

                lines = []
                for acc in current_user.accounts:
                    db.refresh(acc)
                    lines.append(f"Account: {acc.account_number} | Balance: {acc.balance} USD")
                response_str = "BALANCE_DATA\n" + "\n".join(lines)
                conn.sendall(response_str.encode('utf-8'))

            elif command == "TRANSFER":
                if len(parts) < 4:
                    conn.sendall(b"ERROR_BAD_ARGUMENTS")
                    continue

                source_acc_num = parts[1]
                target_acc_num = parts[2]
                try:
                    amount = float(parts[3])
                except ValueError:
                    conn.sendall(b"ERROR_BAD_ARGUMENTS")
                    continue

                description = parts[4] if len(parts) > 4 else ""

                source_account = db.query(models.Account).filter(
                    models.Account.account_number == source_acc_num).with_for_update().first()
                if not source_account or current_user not in source_account.users:
                    conn.sendall(b"ERROR_SOURCE_ACCOUNT_NOT_FOUND")
                    continue

                target_account = db.query(models.Account).filter(
                    models.Account.account_number == target_acc_num).with_for_update().first()
                if not target_account:
                    conn.sendall(b"ERROR_RECIPIENT_NOT_FOUND")
                    continue

                if source_account.id == target_account.id:
                    conn.sendall(b"ERROR_CANNOT_TRANSFER_TO_YOURSELF")
                elif source_account.balance < amount:
                    conn.sendall(b"ERROR_NOT_ENOUGH_BALANCE")
                elif amount <= 0:
                    conn.sendall(b"ERROR_INVALID_AMOUNT")
                else:
                    source_account.balance -= amount
                    target_account.balance += amount

                    recipient_user_id = current_user.id
                    if target_account.users:
                        recipient_user_id = target_account.users[0].id

                    new_tx = models.Transaction(
                        sender_id=current_user.id,
                        recipient_id=recipient_user_id,
                        amount=amount,
                        description=description
                    )
                    db.add(new_tx)

                    for u in target_account.users:
                        new_notification = models.Notification(
                            user_id=u.id,
                            message=f"Account {target_acc_num} received {amount} USD from account {source_acc_num}"
                        )
                        db.add(new_notification)

                    db.commit()
                    conn.sendall(b"TRANSFER_SUCCESS")


            elif command == "HISTORY":
                txs = db.query(models.Transaction).filter(
                    or_(models.Transaction.sender_id == current_user.id,
                    models.Transaction.recipient_id == current_user.id)
                ).all()

                if not txs:
                    conn.sendall(b"HISTORY_EMPTY")
                else:
                    history_lines = []
                    for tx in txs:
                        type = "FROM" if tx.sender_id == current_user.id else "TO"
                        history_lines.append(f"[{tx.timestamp.strftime('%Y-%m-%d %H:%M')}] {type} | Amount: {tx.amount} | Description: {tx.description}")

                    response_str = "HISTORY_DATA\n" + "\n".join(history_lines)
                    conn.sendall(response_str.encode('utf-8'))

            elif command == "NOTIFICATIONS":
                notifications = db.query(models.Notification).filter(models.Notification.user_id == current_user.id).all()

                if not notifications:
                    conn.sendall(b"NOTIFICATIONS_EMPTY")
                else:
                    notif_lines = [n.message for n in notifications]
                    response_str = "NOTIFICATIONS_DATA\n" + "\n".join(notif_lines)
                    conn.sendall(response_str.encode('utf-8'))

            elif command == "DELETE_MY_ACCOUNT":
                if current_user.username == "admin":
                    conn.sendall(b"ERROR_CANNOT_DELETE_ADMIN")
                    continue

                try:
                    accounts_to_check = list(current_user.accounts)
                    for acc in accounts_to_check:
                        current_user.accounts.remove(acc)
                        db.flush()

                        if not acc.users:
                            db.delete(acc)

                    db.query(models.Notification).filter(models.Notification.user_id == current_user.id).delete()

                    db.delete(current_user)
                    db.commit()

                    conn.sendall(b"DELETE_PROFILE_SUCCESS")
                    current_user = None
                except Exception as e:
                    db.rollback()
                    print(f"[ERROR] Failed to delete user account: {e}")
                    conn.sendall(b"ERROR_DATABASE_FAILED")
            elif command == "LEAVE_SHARED_ACCOUNT":
                if len(parts) < 2:
                    conn.sendall(b"ERROR_BAD_ARGUMENTS")
                    continue

                target_acc_num = parts[1]

                account = db.query(models.Account).filter(models.Account.account_number == target_acc_num).with_for_update().first()

                if not account or current_user not in account.users:
                    conn.sendall(b"ERROR_ACCOUNT_NOT_FOUND")
                    continue

                if len(account.users) <=1:
                    conn.sendall(b"ERROR_CANNOT_LEAVE_PERSONAL_ACCOUNT")
                    continue

                try:
                    account.users.remove(current_user)

                    for remaining_user in account.users:
                        new_notification = models.Notification(user_id=remaining_user.id, message=f"User {current_user.username} has left the SHARED ACCOUNT ({target_acc_num})")
                        db.add(new_notification)

                        db.commit()
                        conn.sendall(b"LEAVE_SHARED_ACCOUNT_SUCCESS")
                except Exception as e:
                    db.rollback()
                    print(f"[ERROR] Failed to leave shared account: {e}")
                    conn.sendall(b"ERROR_DATABASE_FAILED")


            elif command == "ADMIN_GET_USERS":
                if current_user.username != "admin":
                    conn.sendall(b"ERROR_FORBIDDEN")
                    continue

                users = db.query(models.User).all()
                user_lines = []
                for u in users:
                    acc_info = ", ".join(
                        [f"[{a.account_number}: {a.balance} USD]" for a in u.accounts]) if u.accounts else "No accounts"
                    user_lines.append(f"ID: {u.id} | Login: {u.username} | PESEL: {u.pesel} | Accounts: {acc_info}")

                response_str = "ADMIN_USERS_DATA\n" + "\n".join(user_lines)
                conn.sendall(response_str.encode('utf-8'))

            elif command == "ADMIN_EDIT_USER":
                if current_user.username != "admin":
                    conn.sendall(b"ERROR_FORBIDDEN")
                    continue

                if len(parts) < 3:
                    conn.sendall(b"ERROR_BAD_ARGUMENTS")
                    continue

                target_username = parts[1]
                new_username = parts[2]

                if target_username == "admin":
                    conn.sendall(b"ERROR_CANNOT_EDIT_ADMIN")
                    continue

                user_to_edit = db.query(models.User).filter(models.User.username == target_username).first()

                if not user_to_edit:
                    conn.sendall(b"ERROR_USER_NOT_FOUND")
                else:
                    try:
                        user_to_edit.username = new_username
                        db.commit()
                        conn.sendall(b"SUCCESS_USER_UPDATED")
                    except Exception as e:
                        db.rollback()
                        conn.sendall(b"ERROR_DATABASE_FAILED")



            elif command == "ADMIN_DELETE_USER":
                if current_user.username != "admin":
                    conn.sendall(b"ERROR_FORBIDDEN")
                    continue

                if len(parts) < 2:
                    conn.sendall(b"ERROR_BAD_ARGUMENTS")
                    continue

                target_username = parts[1]

                if target_username == "admin":
                    conn.sendall(b"ERROR_CANNOT_DELETE_ADMIN")
                    continue

                user_to_delete = db.query(models.User).filter(models.User.username == target_username).first()

                if not user_to_delete:
                    conn.sendall(b"ERROR_USER_NOT_FOUND")
                else:
                    db.delete(user_to_delete)
                    db.commit()
                    conn.sendall(b"DELETE_SUCCESS")

            else:
                conn.sendall(b"UNKNOWN_COMMAND")

    except Exception as e:
        print(f"[ERROR] {addr}: {e}")
        db.rollback()
    finally:
        db.close()
        conn.close()
        print(f"[DISCONNECT] Client {addr} disconnected.")

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[START] Server is running on {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()

if __name__ == "__main__":
    start_server()
