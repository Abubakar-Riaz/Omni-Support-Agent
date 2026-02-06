import uuid
from bot import graph

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

def run_agent_test(test_name: str, conversation_steps: list):
    print(f"--------------------------------------------------")
    print(f"Running Test: {test_name}")
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    all_passed = True

    for step in conversation_steps:
        user_input = step['user']
        # We lowercase everything to make matching easier
        expected_keywords = [w.lower() for w in step.get('expect', [])]
        
        print(f"  User: {user_input}")
        
        try:
            events = graph.stream({"messages": [("user", user_input)]}, config=config, stream_mode="values")
            final_response = ""
            for event in events:
                if "messages" in event:
                    msg = event["messages"][-1]
                    if msg.type == "ai":
                        final_response = msg.content

            print(f"  Agent: {final_response.strip()}")

            # Verification: Check if keywords exist in response
            response_lower = final_response.lower()
            missing_words = [word for word in expected_keywords if word not in response_lower]
            
            if missing_words:
                print(f"  {RED}FAIL: Expected {missing_words}{RESET}")
                all_passed = False
            else:
                print(f"  {GREEN}PASS{RESET}")

        except Exception as e:
            print(f"  {RED}ERROR: {e}{RESET}")
            all_passed = False

    if all_passed:
        print(f"{GREEN}>> TEST CASE '{test_name}' PASSED{RESET}\n")
    else:
        print(f"{RED}>> TEST CASE '{test_name}' FAILED{RESET}\n")

if __name__ == "__main__":
    print("Starting Automated Agent Tests...\n")

    # TEST 1: Policy Knowledge
    run_agent_test(
        test_name="Policy check - Stickers",
        conversation_steps=[
            {
                "user": "Can I return a sticker pack?",
                "expect": ["cannot", "final sale"] 
            }
        ]
    )
     
    # TEST 2: Price Check (Updated for Conciseness)
    run_agent_test(
        test_name="DB Check - Price Conversion",
        conversation_steps=[
            {
                "user": "What is the price of order ORD0001?",
                "expect": ["25.99"] # Removed 'delayed' because agent is now concise
            }
        ]
    )
     
    # TEST 3: Memory
    run_agent_test(
        test_name="Memory Persistence",
        conversation_steps=[
            {
                "user": "My order ID is ORD0002.",
                "expect": ["shipped"] 
            },
            {
                "user": "How much did it cost?", 
                "expect": ["89.99"] 
            }
        ]
    )
     
    # TEST 4: Filing Ticket (Updated keywords)
    run_agent_test(
        test_name="Tool Execution - Filing Ticket",
        conversation_steps=[
            {
                "user": "I am very angry about ORD0004 being cancelled. File a complaint.",
                "expect": ["tkt-"] # Relaxed keyword check (accepts 'filed' or 'created')
            }
        ]
    )

    # TEST 5: Cancel Pending Order (ORD0006 is Pending -> Needs Ticket, not Label)
    run_agent_test(
        test_name="Logic Check - Pending Order Cancellation",
        conversation_steps=[
            {
                "user":"My order ID is ORD0006. I want to return it.",
                "expect":["pending"] # Expect agent to notice it's pending
            },
            {
                "user":"OK. Cancel it.",
                "expect":["tkt-"] # Pending orders get Tickets (Cancellations), not Labels
            }
        ]
    )

    # TEST 6: Return Shipped Order (ORD0007 is Shipped -> Needs Label)
    run_agent_test(
        test_name="Tool - Generate Return Label",
        conversation_steps=[
            {
                "user":"My order ID is ORD0007. I want to return it.",
                "expect":["confirm"] # Agent should ask to confirm first
            },
            {
                "user":"Yes, proceed with return",
                "expect":["lbl-"] # NOW we expect the label
            }
        ]
    )