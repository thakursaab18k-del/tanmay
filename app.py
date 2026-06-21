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
# ⚙️ TELEGRAM CREDENTIALS (UPDATED WITH NEW STRING SESSION)
# =====================================================================
API_ID = 30089442   
API_HASH = '842dc7bbd3ce4a4f96194814dcb725a8'  
SESSION_STRING = "1BVtsOIgBuyVmUa7xkoUJmMRdfa3flcRiZZjucVKYINxqqUmWbDu9Tdy9hMe_2sV4prm_1IabRRUr4cAdKRCiYqg69dkpZ9DxYAo4sBie7YwFtxsQSiIXNS8Y2LhJKykE656WzTeUl18XuXi4AsBouKaeT2-IoCJju5Tp52Fy4C-gLryHhgFnMtB5PvwY7YvWROa2MIB4m6eXlaTw3wnoQzXhY9bkgJC_WNr0NNhYW97RVzlaq70vGAXpn4sOu4LqiOP7QyxHlUvnYY3wyN5rg9W-DYshlOmSvEwUJMufWiQC1pprD8WIv5uVLVaOmURfn5zWlzDrG38S4yKHKW004T7JZfH3wos="

# =====================================================================
# 🌐 ENVIRONMENT VARIABLES (FROM RENDER DASHBOARD)
# =====================================================================
AD_MESSAGE = os.getenv("AD_MESSAGE", "Default promotional message! Set AD_MESSAGE in Render.")
INTERVAL = 300  # 5 minutes

# Tracking Sets for tanmay-2.onrender.com Dashboard
joined_groups_count = 0
target_groups = set()  
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# =====================================================================
# 🧪 FLASK WEB SERVER (Live Monitor Dashboard)
# =====================================================================
app = Flask(__name__)

@app.route('/')
def home():
    return f"""
    <html>
        <head>
            <title>Userbot Monitor Dashboard</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f4f6f9; color: #333; }}
                .card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); max-width: 500px; }}
                h2 {{ color: #2c3e50; }}
                .status {{ font-size: 18px; margin: 10px 0; }}
                .highlight {{ font-weight: bold; color: #2980b9; }}
                .success {{ font-weight: bold; color: #27ae60; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h2>📊 Userbot Advertising Status</h2>
                <hr>
                <p class="status">✅ Total Groups Joined: <span class="highlight">{joined_groups_count}</span></p>
                <p class="status">📢 Active Messaging Rotation: <span class="success">{len(target_groups)} GC</span></p>
                <p style="font-size: 12px; color: #7f8c8d; margin-top: 20px;">Status: Active & Running (Refreshes dynamically)</p>
            </div>
        </body>
    </html>
    """

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# =====================================================================
# 🤖 AUTOMATION & EXPLICIT BYPASS UTILITIES
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

async def handle_join_verifications(entity):
    """Background scanner searching for channel locks or verification buttons."""
    await asyncio.sleep(4)
    try:
        async for message in client.iter_messages(entity, limit=6):
            if message.buttons:
                print(f"Verification elements detected in group {entity.id}. Processing bypass...")
                for row in message.buttons:
                    for button in row:
                        if button.url:
                            print(f"🔗 Force join restriction link found: {button.url}")
                            link_data = extract_hash_or_username(button.url)
                            if link_data:
                                await join_group(link_data)
                                await asyncio.sleep(2)
                        
                        if any(word in (button.text or "").lower() for word in ["click", "verify", "join", "human", "link"]):
                            try:
                                await message.click(button)
                                print("Bypass button activated successfully!")
                            except Exception:
                                pass
    except Exception as e:
        print(f"Verification parsing error: {e}")

async def process_and_register(value):
    global joined_groups_count
    link_data = extract_hash_or_username(value)
    if link_data:
        entity = await join_group(link_data)
        if entity:
            joined_groups_count += 1
            # INSTANT ACTION: Har group bina wait kiye messaging loop me turant add hoga
            target_groups.add(entity.id)
            print(f"Registered group {entity.id} for continuous message broadcasting.")
            
            # Security checks side-by-side run hote rahenge bina main thread roke
            client.loop.create_task(handle_join_verifications(entity))

async def load_env_links():
    print("Scanning environment variables for initial group lists...")
    for key, value in os.environ.items():
        if key.upper().startswith("LINK") and value:
            await process_and_register(value)
            await asyncio.sleep(4) # Flood protection buffer

@client.on(events.NewMessage(chats='me'))
async def saved_messages_handler(event):
    text = event.raw_text
    links = re.findall(r'(?:https?://)?t\.me/[^\s]+|@[a-zA-Z0-9_]+', text)
    
    if not links:
        return

    await event.respond("⚡ Processing dynamic links into active rotation...")
    for link in links:
        await process_and_register(link)
        await asyncio.sleep(3)
                
    await event.respond(f"✅ Loop Updated! Total active groups: {len(target_groups)}")

# =====================================================================
# ⏳ BROADCAST ROTATION (5-MINUTE INTERVAL)
# =====================================================================
async def advertising_loop():
    while not client.is_connected():
        await asyncio.sleep(1)
        
    while True:
        if target_groups:
            print(f"Starting broadcast sequence for {len(target_groups)} active channels...")
            for group_id in list(target_groups):
                try:
                    await client.send_message(group_id, AD_MESSAGE)
                    print(f"Message successfully delivered to endpoint: {group_id}")
                    await asyncio.sleep(4.0) # Safe spacing delay
                except Exception as e:
                    print(f"Skipping or wiping restricted group {group_id}: {e}")
                    if "CHAT_WRITE_FORBIDDEN" in str(e) or "USER_BANNED_IN