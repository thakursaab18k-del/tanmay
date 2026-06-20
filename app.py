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
INTERVAL = 300  # 5 minutes (300 seconds)

target_groups = set()
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# =====================================================================
# 🧪 FLASK WEB SERVER
# =====================================================================
app = Flask(__name__)

@app.route('/')
def home():
    return f"<h3>Userbot Status: Active</h3><p>Total Groups Monitored: {len(target_groups)}</p>"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# =====================================================================
# 🤖 AUTOMATION & ADVANCED BYPASS UTILITIES
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
        print(f"Failed to join link {link_data['value']}: {e}")
        return None

async def handle_join_verifications(entity):
    await asyncio.sleep(5)  # Verification bot ka wait karne ke liye thoda extra time
    try:
        async for message in client.iter_messages(entity, limit=6):
            if message.buttons:
                for row in message.buttons:
                    for button in row:
                        if button.url:
                            print(f"🔗 Verification channel link mila: {button.url}. Joining...")
                            link_data = extract_hash_or_username(button.url)
                            if link_data:
                                await join_group(link_data)
                        
                        if any(word in (button.text or "").lower() for word in ["click", "verify", "join", "human"]):
                            try:
                                await message.click(button)
                                print("Verification button clicked successfully!")
                            except Exception:
                                pass
    except Exception as e:
        print(f"Error in verification: {e}")

async def load_env_links():
    print("Checking environment variables for group links...")
    for key, value in os.environ.items():
        if key.upper().startswith("LINK") and value:
            link_data = extract_hash_or_username(value)
            if link_data:
                entity = await join_group(link_data)
                if entity:
                    target_groups.add(entity.id)
                    await handle_join_verifications(entity)
    print(f"Total initial groups loaded: {len(target_groups)}")

@client.on(events.NewMessage(chats='me'))
async def saved_messages_handler(event):
    text = event.raw_text
    links = re.findall(r'(?:https?://)?t\.me/[^\s]+|@[a-zA-Z0-9_]+', text)
    
    if not links:
        return

    await event.respond("⚡ Live links process ho rahe hain...")
    for link in links:
        link_data = extract_hash_or_username(link)
        if link_data:
            entity = await join_group(link_data)
            if entity:
                target_groups.add(entity.id)
                await handle_join_verifications(entity)
                
    await event.respond(f"✅ Loop me total groups: {len(target_groups)}")

# =====================================================================
# ⏳ FIXED 5-MINUTE BROADCAST LOOP
# =====================================================================
async def advertising_loop():
    # wait_until_ready() hata kar client connection check lagaya hai
    while not client.is_connected():
        await asyncio.sleep(1)
        
    while True:
        if target_groups:
            print(f"Broadcasting message to {len(target_groups)} groups...")
            for group_id in list(target_groups):
                try:
                    await client.send_message(group_id, AD_MESSAGE)
                    print(f"Message sent to group ID: {group_id}")
                    await asyncio.sleep(2.0)  # Rate limit se bachne ke liye delay
                except Exception as e:
                    print(f"Could not send message to group {group_id}: {e}")
                    if "CHAT_WRITE_FORBIDDEN" in str(e) or "USER_BANNED_IN_CHANNEL" in str(e):
                        target_groups.discard(group_id)
        await asyncio.sleep(INTERVAL)

async def main():
    await client.start()
    print("Userbot client connected and authenticated!")
    
    # Env variables ke saare links join karenge
    await load_env_links()
    
    # Background ad task start karenge
    client.loop.create_task(advertising_loop())
    await client.run_until_disconnected()

if __name__ == '__main__':
    # Flask thread start karenge Render ke liye
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Main async process run karenge
    asyncio.run(main())