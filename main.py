import io
import re
from contextlib import redirect_stdout
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from functions import initial_checks, final
from tool_func import langgraph_agent_executor
from prompts import sys
from tool_func import messages, guide_tool
import logging
from fastapi.responses import StreamingResponse
import asyncio
from langchain_core.messages import AIMessageChunk, HumanMessage

#logging.basicConfig(
    # level=#logging.INFO,  # Change this to DEBUG for more detailed #logging
    # format='%(asctime)s - %(levelname)s - %(message)s',
    # handlers=[
        #logging.StreamHandler()
    # ]
# )

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def data_streamer(query,file_path):
    logging.info(f"Received Request for SOP Navigation with query: {query} and file path: {file_path}")
    final_message = ""
    messages.clear()
    messages.append(("system", sys))
    logging.debug("Messages cleared and system message added.")
    processed_claim = initial_checks(query)
    res = final(processed_claim)["output"]
    logging.info(f"Timely filing Processed")
    logging.info(f"Processed claim")
    inp = f"file_path: json-files/{file_path}, Claim: {processed_claim}"
    logging.debug(f"First Input to LangGraph agent: {inp}")
    
    async for msg, metadata in langgraph_agent_executor.astream(
        {"messages": [("user", inp)]}, stream_mode="messages"
    ):
        # Stream all messages from the tool node
        if (
            msg.content
            and not isinstance(msg, HumanMessage)
            and metadata["langgraph_node"] == "tools"
            and not msg.name
        ):
            yield str(msg.content)  # Yielding the tool message content
            # await asyncio.sleep(0.5)  # Simulate a delay
        
        # Final message should come from our agent
        if msg.content and metadata["langgraph_node"] == "agent":
            final_message += msg.content
    
    # Yield the final message from the agent
    yield final_message + "\n" + res



@app.get("/hello-world")
def read_root():
    return {"Hello": "World"}



@app.post("/sop_execution/")
async def sop_execution(
    query, file_path="Coordination of Benefits (COB) - All States Medicaid - SOP.json"
):
    
    try:
        return StreamingResponse(data_streamer(query,file_path), media_type='text/event-stream')

    except Exception as e:
        logging.error(f"Error during SOP execution: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

