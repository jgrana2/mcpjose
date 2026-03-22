import pytest
import sqlite3
import os

from core.guard import SubscriptionGuard

@pytest.fixture
def temp_db():
    db_path = "test_accounts.db"
    
    # Setup
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE users (id TEXT PRIMARY KEY, phone_number TEXT UNIQUE, status TEXT);")
    cursor.execute("CREATE TABLE subscriptions (user_id TEXT, mp_subscription_id TEXT PRIMARY KEY, status TEXT, plan_id TEXT);")
    
    cursor.execute("INSERT INTO users VALUES ('user1', '+1234567890', 'active');")
    cursor.execute("INSERT INTO subscriptions VALUES ('user1', 'sub1', 'authorized', 'plan_A');")
    
    cursor.execute("INSERT INTO users VALUES ('user2', '+0987654321', 'active');")
    cursor.execute("INSERT INTO subscriptions VALUES ('user2', 'sub2', 'cancelled', 'plan_A');")
    
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Teardown
    if os.path.exists(db_path):
        os.remove(db_path)

def test_guard_authorized(temp_db):
    guard = SubscriptionGuard(db_path=temp_db)
    
    assert guard.is_authorized("+1234567890") is True
    assert guard.check_access("+1234567890") == ""

def test_guard_unauthorized_cancelled(temp_db):
    guard = SubscriptionGuard(db_path=temp_db)
    
    assert guard.is_authorized("+0987654321") is False
    assert "Access Denied" in guard.check_access("+0987654321")

def test_guard_unauthorized_not_found(temp_db):
    guard = SubscriptionGuard(db_path=temp_db)
    
    assert guard.is_authorized("+5555555555") is False
    assert "Access Denied" in guard.check_access("+5555555555")
