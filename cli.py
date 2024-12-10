"""
This module contains the Cli client for the MCP servers.
"""
import asyncio
import os
import sys
from datetime import datetime
from typing import TypedDict
from langchain_core.messages import HumanMessage, AIMessageChunk, AIMessage
from langgraph.graph.graph import CompiledGraph

from mcp_client.base import (
    load_server_config,
    create_server_parameters,
    convert_mcp_to_langchain_tools,
    initialise_tools
)

async def list_tools() -> None:
    """List available tools from the server."""
    server_config = load_server_config()
    server_params = create_server_parameters(server_config)
    langchain_tools = await convert_mcp_to_langchain_tools(server_params)

    for tool in langchain_tools:
        print(f"{tool.name}")


async def handle_chat_mode():
    """Handle chat mode for the LangChain agent."""
    langchain_tools = await initialise_tools()
    chat_history = []
    is_last_step = False

    while True:
        try:
            user_message = input("\nYou: ").strip()
            if user_message.lower() in ["exit", "quit"]:
                print("Exiting chat mode.")
                break
            if user_message.lower() in ["clear", "cls"]:
                os.system("cls" if sys.platform == "win32" else "clear")
                chat_history = []
                is_last_step = True
                continue

            chat_history.append(HumanMessage(content=user_message))
            input_messages = {
                "messages": chat_history,
                "is_last_step": is_last_step,
                "today_datetime": datetime.now().isoformat(),
            }
            is_last_step = False

            await query_response(input_messages, langchain_tools)
        except Exception as e:
            print(f"\nError processing message: {e}")
            continue


async def query_response(input_messages: TypedDict, agent_executor: CompiledGraph) -> None:
    """
    Processes responses asynchronously for given input messages using an agent executor.

    Parameters:
    input_messages (TypedDict): Input data structured in a dictionary format with keys and values expected by the agent.
    agent_executor (CompiledGraph): The agent executor object that compiles and handles the graph of operations to process input messages.

    Asynchronous Operation:
    The function iterates over each chunk generated by the agent executor's 'astream' method, which processes input messages and returns results in streamed segments. The function processes each chunk using the 'process_chunk' function.

    Output:
    A newline character is printed after processing all chunks to ensure that the output is cleanly formatted with a newline at the end.
    """
    async for chunk in agent_executor.astream(
            input_messages,
            stream_mode=["messages", "values"]
    ):
        process_chunk(chunk)
        if isinstance(chunk, dict) and "messages" in chunk:
            input_messages["messages"].append(AIMessage(content=chunk["messages"][-1].content))

    print("")  # Ensure a newline after the conversation ends


def process_chunk(chunk):
    """
    Processes a given data chunk by determining its type and handling it accordingly.

    The function inspects the type and specific content of the input argument 'chunk'
    to decide which specialized processing function to call. It is designed to handle
    different data structures including tuples and dictionaries, and utilizes specific
    process functions based on the content and structure of 'chunk'.

    Parameters:
    chunk: The data chunk to be processed. This can be either a tuple or a dictionary.
    - If 'chunk' is a tuple and its first element is the string "messages", it invokes
      the function process_message_chunk with the first element of the second element tuple as an argument.
    - If 'chunk' is a dictionary containing the key "messages", it calls process_final_value_chunk.
    - If 'chunk' is a tuple and its first element is the string "values", it calls
      process_tool_calls with the last element from the list under the 'messages' key in the second element dictionary.
    """
    if isinstance(chunk, tuple) and chunk[0] == "messages":
        process_message_chunk(chunk[1][0])
    elif isinstance(chunk, dict) and "messages" in chunk:
        process_final_value_chunk()
    elif isinstance(chunk, tuple) and chunk[0] == "values":
        process_tool_calls(chunk[1]['messages'][-1])


def process_message_chunk(message_chunk):
    """
    Processes a message chunk and prints its content to the console.

    This function takes a message chunk as input. If the message chunk is an instance
    of AIMessageChunk, it retrieves its content and prints it to the console. The
    content is printed incrementally without a newline character, allowing for smooth
    and continuous output of message data.

    Parameters:
        message_chunk (AIMessageChunk): The message chunk to process and print.

    Note:
        The function flushes the output immediately to ensure real-time display of the
        message content.
    """
    if isinstance(message_chunk, AIMessageChunk):
        content = message_chunk.content # Get the content of the message chunk
        if isinstance(content, list):
            extracted_text = ''.join(item['text'] for item in content if 'text' in item)
            print(extracted_text, end="", flush=True)  # Print message content incrementally
        else:
            print(content, end="", flush=True)


def process_final_value_chunk():
    """
    Ensures that a newline character is printed to the standard output and immediately flushed.
    This is typically used to finalize the display of messages in a console or terminal, ensuring that
    output is properly separated on new lines, particularly after the completion of a processing task.

    Note: The `flush=True` parameter is used to force the buffer to flush, ensuring that the newline
    is immediately output to the terminal without waiting for the buffer to fill.
    """
    print("\n", flush=True)  # Ensure a newline after complete message


def process_tool_calls(message):
    """
    Processes a message object to handle tool calls.

    This function checks if the provided message is an instance of AIMessage
    and if it contains any tool calls. If both conditions are met, it formats
    and prints the tool call results using the message's pretty_print method.

    Parameters:
    message (object): The message object to be processed, potentially containing tool calls.
    """
    if isinstance(message, AIMessage) and message.tool_calls:
        message.pretty_print()  # Format and print tool call results


async def interactive_mode():
    """Run the CLI in interactive mode."""
    print("\nWelcome to the Interactive MCP Command-Line Tool")
    print("Type 'help' for available commands or 'quit' to exit")

    while True:
        try:
            command = input(">>> ").strip()
            if not command:
                continue
            should_continue = await handle_command(command)
            if not should_continue:
                return
        except KeyboardInterrupt:
            print("\nUse 'quit' or 'exit' to close the program")
        except EOFError:
            break
        except Exception as e:
            print(f"\nError: {e}")


async def handle_command(command: str):
    """Handle specific commands dynamically."""
    try:
        if command == "list-tools":
            print("\nFetching Tools List...\n")
            # Implement list-tools logic here
            await list_tools()
        elif command == "chat":
            print("\nEntering chat mode...")
            await handle_chat_mode()
            # Implement chat mode logic here
        elif command in ["quit", "exit"]:
            print("\nGoodbye!")
            return False
        elif command == "clear":
            if sys.platform == "win32":
                os.system("cls")
            else:
                os.system("clear")
        elif command == "help":
            print("\nAvailable commands:")
            print("  list-tools    - Display available tools")
            print("  chat          - Enter chat mode")
            print("  clear         - Clear the screen")
            print("  help          - Show this help message")
            print("  quit/exit     - Exit the program")
        else:
            print(f"\nUnknown command: {command}")
            print("Type 'help' for available commands")
    except Exception as e:
        print(f"\nError executing command: {e}")

    return True


def main() -> None:
    """Entry point for the script."""
    asyncio.run(interactive_mode())  # Run the main asynchronous function


if __name__ == "__main__":
    main()  # Execute the main function when script is run directly
