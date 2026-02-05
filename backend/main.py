from bot import graph
import uuid

def run_chat():
    print("---Omni-Support Agent---")

    thread_id=str(uuid.uuid4())

    config={"configurable":{"thread_id":thread_id}}

    while True:
        try:
            user_input=input("User:")
            if user_input.lower() in ['q','quit','exit']:
                print("Exiting...")
                break

            events=graph.stream(
                {"messages":[("user",user_input)]},
                config=config,
                stream_mode="values"
            )

            for event in events:
                if "messages" in event:
                    last_msg=event["messages"][-1]
                    if last_msg.type=="ai" and not last_msg.tool_calls:
                        print(f"Agent: {last_msg.content}")
        except KeyboardInterrupt:
            print("\nUser Interrupted.")
            break
        except Exception as e:
            print(f"An error occurred:{e}")
if __name__=="__main__":
    run_chat()