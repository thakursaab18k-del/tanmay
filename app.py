import os
import asyncio
import re
import threading
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

# =====================================================================
# ⚙️ TELEGRAM CREDENTIALS
# =====================================================================
API_ID = 30089442   
API_HASH = '842dc7bbd3ce4a4f96194814dcb725a8'  
SESSION_STRING = "1BVtsOGsBu2UuBQK2ziIvMsDqnw2Che930z-M-77KcUNl-QTxVciGU6JlnUcQiWS6DHpN-kU1vlZlIk-B0v77UZuXM4Nmu1x7KSag_F9nQvRqPY4a-HsoWMxhCOmBUpCKHacawQC-KeyhCmHxzD8KtRG5woWVWT0-6pQafvXUuQPfbwQy1Mr_yBBZxMwkOVlDS0zy2JFlvLL1ZeRFpXubowuCy_QN-NAK-C-LujeCPnPILCjGx3bGM7lv00eKd7Fp1rd5v0-FaZ2jhp8B1wM4eCtk23RqBVo-tkBVDEP_zOR5HX8glnzFUBfph3JSQHymd7dWR3re5WHYFqmMxQxWFMasfCciFcc="

# =====================================================================
# 🌐 ENVIRONMENT VARIABLES (FROM RENDER DASHBOARD)
# =====================================================================
AD_MESSAGE = os.getenv("AD_MESSAGE", "Default promotional message! Set AD_MESSAGE in Render.")
INTERVAL = 300  # 5 minutes

target_groups = set()
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# =====================================================================
# 🧪 FLASK WEB SERVER
# =====================================================================
app = Flask(__name__)

@app.route('/')
def home():
    return f"<h3>Userbot Status: Running</h3><p>Total Groups Monitored: {len(target_groups)}</p><p>Active IDs: {list(target_groups)}</p>"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# =====================================================================
# 🤖 UTILITIES & INTUITIVE BYPASS SYSTEMS
# =====================================================================
def extract_hash_or_username(link):
    link = link.strip()
    private_match = re.search(r'(?:t\.me\/joinchat\/|t\.me\/\+)([a-zA-Z0-9_\-]+)', link)
    if private_match:
        return {'type': 'private', 'value': private_match.group(1)}
    
    public_match = re.search(r'(?:t\.me\/|@)([a-zA-Z0-9_]+)', link)
    if public_match:
        return {'type': 'public', 'value': public_match.group(1)}
    return None

async def join_group(link_data):
    try:
        if link_data['type'] == 'private':
            result = await client(ImportChatInviteRequest(link_data['value']))
            print(f"Successfully joined private chat: {link_data['value']}")
            return result.chats[0]
        else:
            entity = await client.get_entity(link_data['value'])
            await client(JoinChannelRequest(entity))
            print(f"Successfully joined public chat: {link_data['value']}")
            return entity
    except Exception as e:
        print(f"Join buffer warning for {link_data['value']}: {e}")
        try:
            entity = await client.get_entity(link_data['value'])
            return entity
        except Exception:
            return None

async def handle_join_verifications(entity):
    """Background scanner searching for channel locks or captcha verification buttons."""
    await asyncio.sleep(3)
    try:
        async for message in client.iter_messages(entity, limit=6):
            if message.buttons:
                print(f"Buttons found in group {entity.id}. Checking for lock requirements...")
                for row in message.buttons:
                    for button in row:
                        # Extract and handle mandatory channel join links inside buttons (e.g., DIGI ANTI style)
                        if button.url:
                            print(f"🔗 Mandatory unlock link found: {button.url}. Processing...")
                            link_data = extract_hash_or_username(button.url)
                            if link_data:
                                await join_group(link_data)
                                await asyncio.sleep(2)
                        
                        # Trigger click activation on human/verify inline buttons
                        if any(word in (button.text or "").lower() for word in ["click", "verify", "join", "human", "link"]):
                            try:
                                await message.click(button)
                                print("Bypass step verification button clicked successfully!")
                            except Exception:
                                pass
    except Exception as e:
        print(f"Verification parsing error: {e}")

async def process_and_register(value):
    """Joins a link, registers it for ads instantly, and scans for locks simultaneously."""
    link_data = extract_hash_or_username(value)
    if link_data:
        entity = await join_group(link_data)
        if entity:
            # INSTANT REGISTRATION: Ensures normal groups are added immediately without waiting
            target_groups.add(entity.id)
            print(f"Added group to broadcast rotation: {entity.id}")
            
            # Run the channel-lock/verification check in the background concurrently
            client.loop.create_task(handle_join_verifications(entity))

async def load_env_links():
    print("Checking environment variables for initial group links...")
    for key, value in os.environ.items():
        if key.upper().startswith("LINK") and value:
            await process_and_register(value)
            await asyncio.sleep(4) # Flood protection delay

@client.on(events.NewMessage(chats='me'))
async def saved_messages_handler(event):
    text = event.raw_text
    links = re.findall(r'(?:https?://)?t\.me/[^\s]+|@[a-zA-Z0-9_]+', text)
    
    if not links:
        return

    await event.respond("⚡ Processing live group registrations...")
    for link in links:
        await process_and_register(link)
        await asyncio.sleep(3)
                
    await event.respond(f"✅ Loop configured! Monitored Groups Count: {len(target_groups)}")

# =====================================================================
# ⏳ 5-MINUTE BROADCAST LOOP
# =====================================================================
async def advertising_loop():
    while not client.is_connected():
        await asyncio.sleep(1)
        
    while True:
        if target_groups:
            print(f"Broadcasting message to {len(target_groups)} groups...")
            for group_id in list(target_groups):
                try:
                    await client.send_message(group_id, AD_MESSAGE)
                    print(f"Message successfully sent to: {group_id}")
                    await asyncio.sleep(3.5) # Anti-flood delay
                except Exception as e:
                    print(f"Could not send message to group {group_id}: {e}")
                    if "CHAT_WRITE_FORBIDDEN" in str(e) or "USER_BANNED_IN_CHANNEL" in str(e):
                        target_groups.discard(group_id)
        await asyncio.sleep(INTERVAL)

async def main():
    await client.start()
    print("Userbot client connected and authenticated!")
    
    await load_env_links()
    client.loop.create_task(advertising_loop())
    await client.run_until_disconnected()

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    asyncio.run(main())