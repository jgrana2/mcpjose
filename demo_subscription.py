import asyncio
from core.guard import SubscriptionGuard
from tools.payment_webhook import PaymentWebhookTool

async def run_demo():
    print("\n--- SUBSCRIPTION GUARD DEMO ---\n")
    
    # We will use a unique test number
    phone_number = "+57_test_user_999"
    guard = SubscriptionGuard()
    webhook_handler = PaymentWebhookTool()
    
    print(f"User {phone_number} asks the agent to perform a premium action...")
    
    # 1. Agent tries to use the tool (User hasn't paid)
    print("\n[AGENT] Calling premium_action()...")
    access_error = guard.check_access(phone_number)
    if access_error:
        print(f"[GUARD BLOCKED] -> {access_error}")
        print("[AGENT TO USER] 'I'm sorry, you need to upgrade your plan to use this feature.'")
    else:
        print("[GUARD PASSED] -> Running premium tool!")

    print("\n... User clicks the Mercado Pago link and completes payment ...")
    
    # 2. Mercado Pago sends a webhook behind the scenes
    print("\n[SYSTEM] Received Webhook from Mercado Pago: Subscription Created!")
    mock_payload = {
        "action": "created",
        "type": "subscription",
        "data": {"id": "preapproval_12345"},
        "status": "authorized",
        "user_id": "test_uuid_999",
        "phone_number": phone_number  # Pass the real phone number here
    }
    result = webhook_handler.process_webhook(mock_payload)
    print(f"[DATABASE] {result['message']}")
    
    print("\n... User asks the agent to perform the premium action again ...")
    
    # 3. Agent tries to use the tool again (User has paid)
    print("\n[AGENT] Calling premium_action()...")
    access_error = guard.check_access(phone_number)
    if access_error:
        print(f"[GUARD BLOCKED] -> {access_error}")
    else:
        print("[GUARD PASSED] -> Access Granted! Running premium tool...")
        print("[AGENT TO USER] 'Here is your completed premium analysis!'")
        
    print("\n--- DEMO COMPLETE ---\n")

if __name__ == "__main__":
    asyncio.run(run_demo())
