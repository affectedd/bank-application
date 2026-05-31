# 🏦 Multi-Threaded Socket Bank Application

A lightweight, high-performance, and completely standalone banking application built using **Python TCP Sockets**, multi-threading, and **SQLAlchemy ORM with SQLite**. 

This repository contains both the concurrent backend server processing transactional logic and an interactive terminal-based client application featuring an administrative control panel.

---

## ✨ Features

### 👤 Client Functionality
* **Secure Registration & Login:** User management with robust password hashing via `bcrypt`.
* **Real-time Balance Check:** Instant updates on current account funds.
* **Atomic Fund Transfers:** Secure peer-to-peer transactions utilizing row-level database locking to prevent race conditions.
* **Transaction History:** Detailed ledger showing all sent and received transfers with custom descriptions and timestamps.
* **In-app Notifications:** Automatic alert generation for incoming funds upon login.

### 👑 Administrative Control Panel
* **Dedicated Admin Role:** Secure separation of concerns—entering the `admin` account unlocks global moderation tools.
* **Global Account Auditing:** Full view of all registered user profiles, database IDs, and current account balances.
* **Account Moderation:** Ability to safely remove users from the system with cascading database cleanup.

---

## 🛠️ Architecture & Tech Stack

* **Language:** Python 3.10+
* **Networking:** Pure TCP Sockets (`socket` module) using a custom plain-text protocol.
* **Concurrency:** Multi-threading (`threading` module) utilizing standalone daemon threads to isolate individual client sessions seamlessly.
* **Database (ORM):** SQLAlchemy 2.0 with an embedded **SQLite** storage file—making the entire ecosystem fully portable (Zero-Configuration/Standalone).
* **Security:** `bcrypt` for one-way cryptographic password hashing.

---

## 📂 Repository Structure

```text
BankApplication/
│
├── app/
│   ├── __init__.py      # Package initializer
│   ├── auth.py          # Cryptographic hashing & verification logic
│   ├── database.py      # SQLite configuration & session factory
│   └── models.py        # SQLAlchemy DDL schemas (Users, Transactions, Notifications)
│
├── server.py            # Main multi-threaded TCP server
├── client.py            # Terminal client interface (User & Admin modes)
├── .gitignore           # Excludes virtual environments and temporary databases
└── README.md            # Project documentation
```

## 🚀 Getting Started
### 1. Prerequisites & Installation
Clone the repository and install the required dependencies (it is highly recommended to use a virtual environment):

```bash
# Clone the repository
git clone https://github.com/affectedd/bank-application
cd BankApplication

# Install dependencies
pip install -r requirements.txt
```

### 2. Running the Server
Initialize the core banking system. The SQLite database (bank.db) and all required tables will be generated automatically on the first boot.

```bash
python server.py
```

### 3. Running the Client
Open a separate terminal window and launch the user/admin terminal interface:
```
python client.py
```
Note: To explore the admin panel, register and log in using the username admin.

---

## 📝 Conceptual Details

* **Why SQLite instead of PostgreSQL?** SQLite acts as an embedded, serverless database engine running inside the Python process itself. This fulfills the portable application requirements while completely removing external infrastructure dependencies like Docker or dedicated DBMS hosting.
* **Data Consistency:** Thread-safe monetary transfers are guaranteed by implementing database-level row-locking via `.with_for_update()`, eliminating any potential double-spending vulnerabilities (Race Conditions) during concurrent socket requests.