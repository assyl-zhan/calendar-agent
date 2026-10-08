from anthropic import Anthropic
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import os
import json

load_dotenv()


client = Anthropic(api_key=os.getenv("API_KEY"))

tz = timezone(timedelta(hours=5))

def current_date():
    now = datetime.now(tz=tz)
    return now

def weekday():
    day = datetime.now(tz=tz)
    return day.strftime("%A")


system_prompt = f"""
You are a calendar assistant. You help the user create calendar events through conversation.

# Current date and time
Now: {current_date().strftime("%Y-%m-%d %H:%M")}
Day of week: {weekday()}
Timezone: UTC+5 (Asia/Almaty)

Use this as the reference for relative dates like "tomorrow" or "next Monday". Work out weekdays carefully from this date.

# What an event needs
Every event requires ALL of these:
1. Title
2. Date
3. Start time
4. End time (or a duration, which you convert to an end time)

# Missing information
- If any required field is missing, ask for it. Never invent or assume a value.
- Vague times like "afternoon" or "evening" are not start times. Ask for the exact time.
- Ask about everything that is missing in ONE message, not one question per turn.

# Dates and times
- The user writes dates as DD.MM.YYYY (06.10.2026 = 6 October 2026). If a date could still be read two ways, ask.
- Interpret "this Friday" as the next upcoming Friday, including today if today is Friday and the time has not passed. If the meaning is unclear, ask.
- Use 24-hour time.
- Always state the full date with the weekday when you summarize (e.g. "Friday, 2026-10-09").

# Validation (check before asking for confirmation)
- If the start time is in the past, tell the user and ask for a new time.
- If the end time is not after the start time, tell the user and ask for a correction.

# Confirmation before creating
- When you have all four fields and they pass validation, do NOT call the tool yet.
- Show a short summary: title, date with weekday, start time, end time.
- Ask: "Should I create this?"
- Call create_event ONLY after an explicit yes ("yes", "ok", "create it"). If the user changes anything, update the summary and ask again.

# Tool use
- create_event takes: title, start, end. Start and end are ISO 8601 with the offset, e.g. 2026-10-09T15:00:00+05:00.
- Create one event per tool call. If the user requests several events, list them all, get one confirmation, then create them one by one.
- Never tell the user an event was created until you receive a successful tool result.
- If the tool returns an error, tell the user what failed and ask how to proceed. Do not retry silently.

# Style
- Short and direct. No filler, no repeated praise or apologies.
- Reply in the language the user writes in.
- If the user asks for something outside calendar events, say you only handle creating events."""

tools = [
    {
    "name": "create_event",
   
    "description": (
        "Creates a single calendar event. Call this ONLY after the user has "
        "explicitly confirmed the event summary. Never call it with guessed "
        "or missing values. Creates one event per call."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Short event title, e.g. 'English lesson with Aruzhan'."
            },
            "start": {
                "type": "string",
                
                "description": (
                    "Start date and time in ISO 8601 with UTC offset, "
                    "e.g. 2026-10-09T15:00:00+05:00."
                )
            },
            "end": {
                "type": "string",
                "description": (
                    "End date and time in ISO 8601 with UTC offset, "
                    "e.g. 2026-10-09T16:00:00+05:00. Must be after start."
                )
            }
        },
      
        "required": ["title", "start", "end"]
    }
}
]

def create_event(title, start, end):
    print(f"[FAKE EVENT]: Event {title} create at {start} - {end}!")

    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
    except ValueError:
        return json.dumps({"status": "error", "message": "start/end must be ISO 8601 with offset"})
    if end_dt <= start_dt:
        return json.dumps({"status": "error", "message": "end must be after start"})
    elif start_dt < datetime.now(tz=tz):
        return json.dumps({"status": "error", "message": "no past events can be created"})

    return json.dumps({"status": "created"})

def run_tool(name, tool_input):

    if name == "create_event":
        return create_event(**tool_input)
    return json.dumps({"status": "error", "message": f"unknown tool : {name}"})


user_input = input("Write your prompt here: ")
messages = [{"role": "user", "content": user_input}]

event_created = False

while True:

    response = client.messages.create(
        max_tokens=1024,
        model="claude-sonnet-5",
        messages=messages,
        system=system_prompt,
        tools=tools
    )

    if response.stop_reason == "end_turn":
        for block in response.content:
            if block.type == "text":
                print(block.text)
        
        messages.append({"role": "assistant", "content": response.content})

        if event_created:
            break

        input_1 = input("Write here: ")
        if input_1.strip().lower() in ("quit", "exit"):
            break
        messages.append({"role": "user", "content": input_1})

    elif response.stop_reason == "tool_use":
        tool_results = []

        for block in response.content:
            if block.type == "tool_use":
                result = run_tool(block.name, block.input)

                if json.loads(result).get("status") == "created":
                    event_created = True

                tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                    "is_error": json.loads(result).get("status") != "created"
                }
                )


        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    else:
        messages.append({"role": "assistant", "content": "unexpected stop reason behaviour"})
        break

    