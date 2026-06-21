import os
import asyncio
import re
import threading
from datetime import datetime
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.errors import FloodWaitError, UserBannedInChannelError, ChatWriteForbiddenError

# =====================================================================
# ⚙️ CONFIGURATION FOR HIGH-TRUST AGED ACCOUNTS
# =====================================================================
API_ID = 30089442   
API_HASH = '842dc7bbd3ce4a4f96194814dcb725a8'  
SESSION_STRING = "1BVtsOIgBuyVmUa7xkoUJmMRdfa3flcRiZZjucVKYINxqqUmWbDu9Tdy9hMe_2sV4prm_1IabRRUr4cAdKRCiYqg69dkpZ9DxYAo4sBie7YwFtxsQSiIXNS8Y2LhJKykE656WzTeUl18XuXi4AsBouKaeT2-IoCJju5Tp52Fy4C-gLryHhgFnMtB5PvwY7YvWROa2MIB4m6eXlaTw3wnoQzXhY9bkgJC_WNr0NNhYW97RVzlaq70vGAXpn4sOu4LqiOP7QyxHlUvnYY3wyN5rg9W-DYshlOmSvEwUJMufWiQC1pprD8WIv5uVLVaOmURfn5zWlzDrG38S4yKHKW004T7JZfH3wos="

AD_MESSAGE = os.getenv("AD_MESSAGE", "Default promotional message! Set AD_MESSAGE in Render.")
INTERVAL = 900     # 15 minutes optimal broadcast sleep loop
SEND_DELAY = 12    # Optimized 12s delay between messages (Extremely safe for 3-year old accounts)

# Global Memory Storage for Analytics
all_submitted_links = set()
target_groups = {}  # {group_id: {"title": title, "last_sent": time}}
failed_groups = {}  # {link: {"reason": reason, "time": time}}
total_messages_sent = 0
last_cycle_timestamp = "Pending..."
is_broadcasting = False

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
app = Flask(__name__)

# =====================================================================
# 📊 PREMIUM FLASK CYBERPUNK DASHBOARD INTERFACE
# =====================================================================
@app.route('/')
def home():
    # Render Active Loop Row Elements
    active_rows = ""
    if target_groups:
        for gid, data in target_groups.items():
            active_rows += f"""
            <tr style="border-bottom: 1px solid #334155;">
                <td style="padding: 12px; color: #38bdf8;">⚡ {gid}</td>
                <td style="padding: 12px; color: #f1f5f9; font-weight: 500;">{data['title']}</td>
                <td style="padding: 12px;"><span style="background: rgba(34, 197, 94, 0.2); color: #4ade80; padding: 4px 8px; border-radius: 4px; font-size: 12px;">🟢 {data['last_sent']}</span></td>
            </tr>
            """
    else:
        active_rows = "<tr><td colspan='3' style='text-align:center; padding:20px; color:#64748b;'>No endpoints currently locked in rotation loop.</td></tr>"

    # Render Failure Diagnostic Row Elements
    failed_rows = ""
    if failed_groups:
        for link, data in failed_groups.items():
            failed_rows += f"""
            <tr style="border-bottom: 1px solid #334155;">
                <td style="padding: 12px; color: #94a3b8; font-size:13px;">{link}</td>
                <td style="padding: 12px;"><span style="background: rgba(239, 68, 68, 0.2); color: #f87171; padding: 4px 8px; border-radius: 4px; font-size: 12px;">⚠️ {data['reason']}</span></td>
                <td style="padding: 12px; color: #64748b; font-size:12px;">{data['time']}</td>
            </tr>
            """
    else:
        failed_rows = "<tr><td colspan='3' style='text-align:center; padding:20px; color:#4ade80;'>Clear operational matrix. Zero transmission blocks!</td></tr>"

    status_badge = '<span style="background:#22c55e; color:white; padding:6px 12px; border-radius:20px; font-size:14px; box-shadow: 0 0 10px #22c55e;">● BROADCAST ACTIVE</span>' if is_broadcasting else '<span style="background:#eab308; color:black; padding:6px 12px; border-radius:20px; font-size:14px; font-weight:bold;">● COOLDOWN CYCLE</span>'

    return f"""
    <!DOCTYPE html>
    <html>
        <head>
            <title>Userbot Engine Control Panel</title>
            <meta http-equiv="refresh" content="15">
            <style>
                body {{ background: #0f172a; color: #e2e8f0; font-family: 'Inter', system-ui, sans-serif; margin: 0; padding: 40px; }}
                .container {{ max-width: 1000px; margin: 0 auto; }}
                .header-panel {{ background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border: 1px solid #334155; border-radius: 16px; padding: 30px; margin-bottom: 30px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3); }}
                .metrics-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-top: 25px; }}
                .metric-card {{ background: #1e293b; border: 1px solid #334155; padding: 20px; border-radius: 12px; text-align: center; border-top: 4px solid #38bdf8; }}
                .metric-title {{ font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; }}
                .metric-value {{ font-size: 28px; font-weight: 700; color: #f8fafc; margin-top: 5px; }}
                .data-card {{ background: #1e293b; border: 1px solid #334155; border-radius: 16px; padding: 25px; margin-bottom: 30px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }}
                .card-title {{ font-size: 18px; font-weight: 600; color: #f1f5f9; margin-top: 0; border-bottom: 1px solid #334155; padding-bottom: 15px; display: flex; justify-content: space-between; align-items: center; }}
                table {{ width: 100%; border-collapse: collapse; text-align: left; }}
                th {{ padding: 12px; color: #94a3b8; font-size: 13px; text-transform: uppercase; border-bottom: 2px solid #334155; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header-panel">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h1 style="margin: 0; font-size: 26px; font-weight: 800; letter-spacing: -0.5px; color: #f8fafc;">⚡ Userbot Scale Architecture</h1>
                        {status_badge}
                    </div>
                    <div class="metrics-grid">
                        <div class="metric-card" style="border-top-color: #38bdf8;">
                            <div class="metric-title">Submitted Targets</div>
                            <div class="metric-value">{len(all_submitted_links)}</div>
                        </div>
                        <div class="metric-card" style="border-top-color: #4ade80;">
                            <div class="metric-title">Active Sync (GC)</div>
                            <div class="metric-value">{len(target_groups)}</div>
                        </div>
                        <div class="metric-card" style="border-top-color: #fbbf24;">
                            <div class="metric-title">Total Ads Transmitted</div>
                            <div class="metric-value">{total_messages_sent}</div>
                        </div>
                        <div class="metric-card" style="border-top-color: #f87171;">
                            <div class="metric-title">Blocked/Muted Links</div>
                            <div class="metric-value">{len(failed_groups)}</div>
                        </div>
                    </div>
                    <p style="margin-top:20px; margin-bottom:0; font-size:13px; color:#64748b;"><b>Last Complete Cycle Timestamp:</b> {last_cycle_timestamp} | Account Profile Status: Aged Verified (3yr Gold Account)</p>
                </div>

                <div class="data-card">
                    <div class="card-title">🟢 Active Live Transmission Channels</div>
                    <table>
                        <thead>
                            <tr><th>Target Chat Identifier</th><th>Group Title Mapping</th><th>Last Transmission Receipt</th></tr>
                        </thead>
                        <tbody>{active_rows}</tbody>
                    </table>
                </div>

                <div class="data-card">
                    <div class="card-title" style="color: #f87171;">⚠️ System Restriction Log Matrix</div>
                    <table>
                        <thead>
                            <tr><th>Failed Source Link Block</th><th>Validation Rejection Reason</th><th>Detection Execution Time</th></tr>
                        </thead>
                        <tbody>{failed_rows}</tbody>
                    </table>
                </div>
            </div>
        </body>
    </html>
    """

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

# =====================================================================
# 🤖 UTILITIES & AUTO-REFRESHER PIPELINE
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

async def join_group(link_data, raw_link):
    try:
        if link_data['type'] == 'private':
            result = await client(ImportChatInviteRequest(link_data['value']))
            return result.chats[0]
        else:
            entity = await client.get_entity(link_data['value'])
            await client(JoinChannelRequest(entity))
            return entity
    except FloodWaitError as fwe:
        failed_groups[raw_link] = {"reason": f"Flood restriction delay: {fwe.seconds}s", "time": datetime.now().strftime('%H:%M:%S')}
        await asyncio.sleep(fwe.seconds)
        return None
    except Exception:
        try:
            return await client.get_entity(link_data['value'])
        except Exception as e:
            failed_groups[raw_link] = {"reason": f"Join Denied ({str(e)})", "time": datetime.now().strftime('%H:%M:%S')}
            return None

async def handle_join_verifications(entity):
    await asyncio.sleep(4)
    try:
        async for message in client.iter_messages(entity, limit=6):
            if message.buttons:
                for row in message.buttons:
                    for button in row:
                        if button.url:
                            link_data = extract_hash_or_username(button.url)
                            if link_data:
                                await join_group(link_data, button.url)
                                await asyncio.sleep(2)
                        if any(word in (button.text or "").lower() for word in ["click", "verify", "join", "human", "link"]):
                            try:
                                await message.click(button)
                            except Exception:
                                pass
    except Exception:
        pass

async def process_and_register(value):
    value = value.strip()
    if not value or value in all_submitted_links:
        return
    all_submitted_links.add(value)
    
    link_data = extract_hash_or_username(value)
    if not link_data:
        failed_groups[value] = {"reason": "Malformed link format", "time": datetime.now().strftime('%H:%M:%S')}
        return
        
    entity = await join_group(link_data, value)
    if entity:
        if value in failed_groups:
            del failed_groups[value]
        title = getattr(entity, 'title', 'Public Chat Room')
        if entity.id not in target_groups:
            target_groups[entity.id] = {"title": title, "last_sent": "Waiting for cycle..."}
        client.loop.create_task(handle_join_verifications(entity))

async def load_env_links():
    for key, value in os.environ.items():
        if key.upper().startswith("LINK") and value:
            await process_and_register(value)
            await asyncio.sleep(4)

@client.on(events.NewMessage(chats='me'))
async def saved_messages_handler(event):
    text = event.raw_text
    links = re.findall(r'(?:https?://)?t\.me/[^\s]+|@[a-zA-Z0-9_]+', text)
    if not links:
        return

    await event.respond("⚡ **Dynamic 100+ Bulk Ingestion Initiated...**\nParsing sheets and establishing handshakes.")
    for link in links:
        await process_and_register(link)
        await asyncio.sleep(2)
    await event.respond(f"✅ **Ingestion Complete!**\nTotal synchronized loop size: {len(target_groups)} active channels.")

# =====================================================================
# ⏳ HIGH-SCALE ADVERTISING ROTATION CORE LOOP
# =====================================================================
async def advertising_loop():
    global total_messages_sent, last_cycle_timestamp, is_broadcasting
    while not client.is_connected():
        await asyncio.sleep(1)
        
    while True:
        if target_groups:
            is_broadcasting = True
            for group_id, info in list(target_groups.items()):
                try:
                    await client.send_message(group_id, AD_MESSAGE)
                    total_messages_sent += 1
                    target_groups[group_id]["last_sent"] = datetime.now().strftime('%H:%M:%S')
                    await asyncio.sleep(SEND_DELAY)
                except FloodWaitError as fwe:
                    await asyncio.sleep(fwe.seconds)
                except (UserBannedInChannelError, ChatWriteForbiddenError):
                    failed_groups[f"ID: {group_id}"] = {"reason": "Muted/Banned from Chat Workspace", "time": datetime.now().strftime('%H:%M:%S')}
                    if group_id in target_groups:
                        del target_groups[group_id]
                except Exception:
                    pass
            is_broadcasting = False
            last_cycle_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        await asyncio.sleep(INTERVAL)

async def main():
    await client.start()
    await load_env_links()
    client.loop.create_task(advertising_loop())
    await client.run_until_disconnected()

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    asyncio.run(main())