import socket
import threading
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.auth import verify_password, get_password_hash
from app import models
from sqlalchemy import or_

models.Base.metadata.create_all(bind=engine)
HOST = '127.0.0.1'
PORT = 65432

def handle_client(conn, addr):
    print(f"[New Connection] {addr} connected.")
    db: Session = SessionLocal()
    current_user = None

    try:
        while True:
            data = conn.recv(1024).decode('utf-8')
            if not data:
                break

            parts = data.strip().split(maxsplit=3)
            if not parts:
                continue

            command = parts[0].upper()

            if command == "REGISTER":
                if len(parts) < 3:
                    conn.sendall(b"ERROR_BAD_ARGUMENTS")
                    continue
                username, password = parts[1], parts[2]
                existing_user = db.query(models.User).filter(models.User.username == username).first()
                if existing_user:
                    conn.sendall(b"ERROR_USER_EXISTS")
                else:
                    hashed=get_password_hash(password)
                    new_user = models.User(username=username, hashed_password=hashed, balance=1000.0)
                    db.add(new_user)
                    db.commit()
                    conn.sendall(b"REGISTER_SUCCESS")



            elif command == "LOGIN":
                username, password = parts[1], parts[2]
                user = db.query(models.User).filter(models.User.username == username).first()
                if user and verify_password(password, user.hashed_password):
                    current_user = user
                    conn.sendall(b"LOGIN_SUCCESS")
                else:
                    conn.sendall(b"LOGIN_FAILED")
            elif not current_user:
                conn.sendall(b"ERROR_UNAUTHORIZED")

            elif command == "BALANCE":
                db.refresh(current_user)
                conn.sendall(f"BALANCE: {current_user.balance}".encode('utf-8'))

            elif command == "TRANSFER":
                recipient_username = parts[1]
                amount = float(parts[2])
                description = parts[3] if len(parts) > 3 else ""

                sender = db.query(models.User).filter(models.User.id == current_user.id).with_for_update().first()
                recipient = db.query(models.User).filter(models.User.username == recipient_username).with_for_update().first()

                if not recipient:
                    conn.sendall(b"ERROR_RECIPIENT_NOT_FOUND")
                elif sender.id == recipient.id:
                    conn.sendall(b"ERROR_CANNOT_TRANSFER_TO_YOURSELF")
                elif sender.balance < amount:
                    conn.sendall(b"ERROR_NOT_ENOUGH_BALANCE")
                elif amount <= 0:
                    conn.sendall(b"ERROR_INSUFFICIENT_BALANCE")
                else:
                    sender.balance -= amount
                    recipient.balance += amount

                    new_tx = models.Transaction(
                        sender_id = sender.id,
                        recipient_id = recipient.id,
                        amount = amount,
                        description = description
                    )
                    db.add(new_tx)

                    new_notification = models.Notification(user_id=recipient.id, message=f"You received the transfer for the amount {amount} from {sender.username}")
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

            elif command == "ADMIN_GET_USERS":
                if current_user.username != "admin":
                    conn.sendall(b"ERROR_FORBIDDEN")
                    continue

                users = db.query(models.User).all()
                user_lines = [f"ID: {u.id} | Login: {u.username} | Balance: {u.balance} USD" for u in users]
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
