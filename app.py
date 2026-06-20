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
INTERVAL = 120  # 2 minutes

# Global tracking structures
target_groups = set()
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# =====================================================================
# 🧪 FLASK WEB SERVER (To satisfy Render Web Service Requirements)
# =====================================================================
app = Flask(__name__)

@app.route('/')
def home():
    return f"<h3>Userbot Status: Running Active</h3><p>Total Groups Monitored: {len(target_groups)}</p>"

def run_flask():
    # Render automatically provides a PORT environment variable
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# =====================================================================
# 🤖 TELETHON AUTOMATION UTILITIES
# =====================================================================
def extract_hash_or_username(link):
    """Parses telegram links to extract public usernames or private invite hashes."""
    link = link.strip()
    private_match = re.search(r'(?:t\.me\/joinchat\/|t\.me\/\+)([a-zA-Z0-9_\-]+)', link)
    if private_match:
        return {'type': 'private', 'value': private_match.group(1)}
    
    public_match = re.search(r'(?:t\.me\/|@)([a-zA-Z0-9_]+)', link)
    if public_match:
        return {'type': 'public', 'value': public_match.group(1)}
    return None

async def join_group(link_data):
    """Attempts to join a group or channel depending on link type."""
    try:
        if link_data['type'] == 'private':
            result = await client(ImportChatInviteRequest(link_data['value']))
            print(f"Successfully joined private chat via hash: {link_data['value']}")
            return result.chats[0]
        else:
            entity = await client.get_entity(link_data['value'])
            await client(JoinChannelRequest(entity))
            print(f"Successfully joined public chat: {link_data['value']}")
            return entity
    except Exception as e:
        print(f"Failed to join link {link_data['value']}: {e}")
        return None

async def handle_join_verifications(entity):
    """Looks for bot verification messages and clicks the first button if found."""
    await asyncio.sleep(3)
    try:
        async for message in client.iter_messages(entity, limit=5):
            if message.buttons and any(word in message.text.lower() for word in ["click", "verify", "welcome", "human"]):
                print(f"Attempting to click verification button in group: {entity.title}")
                await message.click(0)
                break
    except Exception as e:
        print(f"Error while bypassing group verification: {e}")

async def load_env_links():
    """Scans environment variables for any keys starting with 'LINK' and joins them."""
    print("Checking environment variables for group links...")
    for key, value in os.environ.items():
        if key.upper().startswith("LINK") and value:
            print(f"Found env variable {key}: {value}")
            link_data = extract_hash_or_username(value)
            if link_data:
                entity = await join_group(link_data)
                if entity:
                    target_groups.add(entity.id)
                    await handle_join_verifications(entity)
    print(f"Initial setup done. Loaded {len(target_groups)} groups from Environment Variables.")

# Event listener tracking messages you send to your own "Saved Messages" cloud
@client.on(events.NewMessage(chats='me'))
async def saved_messages_handler(event):
    text = event.raw_text
    links = re.findall(r'(?:https?://)?t\.me/[^\s]+|@[a-zA-Z0-9_]+', text)
    
    if not links:
        return

    await event.respond("⚡ Processing live links... Automated verification bypass active.")
    for link in links:
        link_data = extract_hash_or_username(link)
        if link_data:
            entity = await join_group(link_data)
            if entity:
                target_groups.add(entity.id)
                await handle_join_verifications(entity)
                
    await event.respond(f"✅ Active groups in loop: {len(target_groups)}")

async def advertising_loop():
    """Independent background routine pushing your custom message every 2 minutes."""
    await client.wait_until_ready()
    while True:
        if target_groups:
            print(f"Broadcasting custom ad message to {len(target_groups)} groups...")
            for group_id in list(target_groups):
                try:
                    await client.send_message(group_id, AD_MESSAGE)
                    await asyncio.sleep(1.5) # Anti-flood delay
                except Exception as e:
                    print(f"Could not send message to group {group_id}: {e}")
                    if "CHAT_WRITE_FORBIDDEN" in str(e) or "USER_BANNED_IN_CHANNEL" in str(e):
                        target_groups.discard(group_id)
        await asyncio.sleep(INTERVAL)

async def main():
    await client.start()
    print("Userbot client authenticated via String Session!")
    
    # Process environmental links (LINK1, LINK2, etc.) right after startup
    await load_env_links()
    
    # Run the advertising clock task completely in the background
    client.loop.create_task(advertising_loop())
    
    # Keep the userbot active
    await client.run_until_disconnected()

if __name__ == '__main__':
    # 1. Start Flask web server thread so Render marks the Web Service as "Live"
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # 2. Run the main asynchronous Telethon workflow
    asyncio.run(main())