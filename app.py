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
    return f"<h3>Userbot Status: Active & Running</h3><p>Total Groups Monitored: {len(target_groups)}</p><p>Active Group IDs: {list(target_groups)}</p>"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# =====================================================================
# 🤖 AUTOMATION & DUAL-MODE BYPASS UTILITIES
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
        print(f"Join warning/limit for {link_data['value']}: {e}")
        try:
            entity = await client.get_entity(link_data['value'])
            return entity
        except Exception:
            return None

async def process_group_by_mode(entity):
    """
    Dual-Mode Logic: Automatically detects if a group is normal 
    or has a verification bot setup.
    """
    if not entity:
        return
        
    print(f"Analyzing security mode for group: {entity.title} (ID: {entity.id})")
    await asyncio.sleep(4)  # Security bot message standard trigger time
    
    has_verification_bot = False
    
    try:
        async for message in client.iter_messages(entity, limit=5):
            if message.buttons:
                has_verification_bot = True
                print(f"[MODE: Verification Bot Detected] Processing security lock buttons...")
                for row in message.buttons:
                    for button in row:
                        if button.url:
                            print(f"🔗 Force join link found: {button.url}")
                            link_data = extract_hash_or_username(button.url)
                            if link_data:
                                await join_group(link_data)
                                await asyncio.sleep(2)
                        
                        if any(word in (button.text or "").lower() for word in ["click", "verify", "join", "human", "link"]):
                            try:
                                await message.click(button)
                                print("Clicked bypass button.")
                            except Exception:
                                pass
                break
    except Exception as e:
        print(f"Error checking group buttons: {e}")

    # [MODE: Normal Group or Verification Cleared]
    # Agar group normal hai ya verification bypass ho gayi hai, list me save karo
    target_groups.add(entity.id)
    print(f"Added to active ad loop rotation: {entity.title} (Total: {len(target_groups)})")

async def load_env_links():
    print("Scanning Environment Variables for initial links...")
    for key, value in os.environ.items():
        if key.upper().startswith("LINK") and value:
            link_data = extract_hash_or_username(value)
            if link_data:
                entity = await join_group(link_data)
                if entity:
                    await process_group_by_mode(entity)
                    await asyncio.sleep(4) # Flood protection

@client.on(events.NewMessage(chats='me'))
async def saved_messages_handler(event):
    text = event.raw_text
    links = re.findall(r'(?:https?://)?t\.me/[^\s]+|@[a-zA-Z0-9_]+', text)
    
    if not links:
        return

    await event.respond("⚡ Intelligent Auto-Mode Processing Activated...")
    for link in links:
        link_data = extract_hash_or_username(link)
        if link_data:
            entity = await join_group(link_data)
            if entity:
                await process_group_by_mode(entity)
                await asyncio.sleep(3)
                
    await event.respond(f"✅ Configuration Saved! Monitored Groups Count: {len(target_groups)}")

# =====================================================================
# ⏳ INTELLIGENT 5-MINUTE BROADCAST LOOP
# =====================================================================
async def advertising_loop():
    while not client.is_connected():
        await asyncio.sleep(1)
        
    while True:
        if target_groups:
            print(f"Starting broadcast sequence for {len(target_groups)} active endpoints...")
            for group_id in list(target_groups):
                try:
                    await client.send_message(group_id, AD_MESSAGE)
                    print(f"Ad pushed successfully to group ID: {group_id}")
                    await asyncio.sleep(4.0)  # Safe delay between messages
                except Exception as e:
                    print(f"Skipping or cleaning restricted group {group_id}: {e}")
                    if "CHAT_WRITE_FORBIDDEN" in str(e) or "USER_BANNED_IN_CHANNEL" in str(e):
                        target_groups.discard(group_id)
        await asyncio.sleep(INTERVAL)

async def main():
    await client.start()
    print("Userbot client successfully authenticated and live!")
    
    await load_env_links()
    client.loop.create_task(advertising_loop())
    await client.run_until_disconnected()

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    asyncio.run(main())