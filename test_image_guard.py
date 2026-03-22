from langchain_agent.tool_registry import ProjectToolRegistry

def test_generate_image_guard():
    registry = ProjectToolRegistry()
    
    # 1. Try with an unauthorized number explicitly
    print("--- Testing Unauthorized Number ---")
    res1 = registry.generate_image(prompt="a cute cat", phone_number="+5700000000")
    print("Result:", res1)
    
    # 2. Add an authorized number to the db directly for the default user
    print("\n--- Testing Authorized Default Number ---")
    import os
    import sqlite3
    
    # Override the environment variable for testing
    os.environ["WHATSAPP_DEFAULT_DESTINATION"] = "+5711111111"
    
    with sqlite3.connect("accounts.db") as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO users (id, phone_number) VALUES ('u1', '+5711111111')")
        cursor.execute("INSERT OR REPLACE INTO subscriptions (user_id, mp_subscription_id, status) VALUES ('u1', 'sub_111', 'authorized')")
        conn.commit()

    try:
        # Don't pass a phone number, it should fallback to the default destination!
        res2 = registry.generate_image(prompt="a cute cat")
        if 'error' in res2 and 'Access Denied' in res2['error']:
            print("Guard incorrectly blocked authorized default user!")
        else:
            print("Guard allowed default user! API Result:", res2)
    except Exception as e:
        print("Exception after passing guard:", e)

if __name__ == "__main__":
    test_generate_image_guard()
