import os, re, sqlite3, logging
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)
TOKEN = os.environ.get('BOT_TOKEN', '').strip()
ADMIN_ID = int(os.environ.get('ADMIN_ID', '6871050893'))
CHANNEL = os.environ.get('FORCE_CHANNEL', '@BankingTitanss').strip()
CHANNEL_URL = os.environ.get('FORCE_CHANNEL_URL', 'https://t.me/BankingTitanss').strip()
UPI_ID = os.environ.get('UPI_ID', 'YOUR_UPI_ID_HERE').strip()
UPI_QR_URL = os.environ.get('UPI_QR_URL', '').strip()
DB_PATH = os.environ.get('DB_PATH', 'fire_extractor.db')
PLANS = {'7d': ('7 Days', 99, 7), '28d': ('28 Days', 299, 28), 'life': ('Lifetime', 599, None)}
URL_RE = re.compile(r'https?://[^\s\"\'<>]+', re.I)

def db():
    c = sqlite3.connect(DB_PATH)
    c.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, premium_until TEXT, lifetime INTEGER DEFAULT 0)')
    c.execute('CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, plan TEXT, utr TEXT, status TEXT DEFAULT "pending", created TEXT)')
    c.commit(); return c

def is_premium(uid):
    c=db(); row=c.execute('SELECT premium_until,lifetime FROM users WHERE user_id=?',(uid,)).fetchone(); c.close()
    if not row: return False
    if row[1]: return True
    if row[0]:
        try: return datetime.fromisoformat(row[0]) > datetime.now(timezone.utc)
        except Exception: pass
    return False

async def joined(update, context):
    try:
        m = await context.bot.get_chat_member(CHANNEL, update.effective_user.id)
        return m.status in ('member','administrator','creator') or (m.status == 'restricted' and getattr(m, 'is_member', False))
    except Exception as e:
        logging.warning('Channel membership check failed: %s', e)
        return False

async def force_gate(update, context):
    if update.effective_user.id == ADMIN_ID: return True
    if await joined(update, context): return True
    kb = InlineKeyboardMarkup([[InlineKeyboardButton('📢 Join Channel', url=CHANNEL_URL)], [InlineKeyboardButton('✅ Joined — Check Again', callback_data='check_join')]])
    msg = 'Fire Extractor use karne se pehle channel join karo, phir Check Again dabao.'
    if update.callback_query: await update.callback_query.message.reply_text(msg, reply_markup=kb)
    else: await update.effective_message.reply_text(msg, reply_markup=kb)
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await force_gate(update, context): return
    kb = InlineKeyboardMarkup([[InlineKeyboardButton('💎 Buy Premium', callback_data='plans')], [InlineKeyboardButton('ℹ️ My Plan', callback_data='myplan')]])
    await update.message.reply_text('🔥 Welcome to Fire Extractor\n\nAuthorized TXT/HTML files upload karo; bot unmein se URLs extract karega. APK/DRM ya paid-content restrictions bypass nahi karta.', reply_markup=kb)

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    if q.data == 'check_join':
        if await joined(update, context): await q.message.reply_text('✅ Channel membership verified. /start dabao.')
        else: await q.message.reply_text('Abhi membership confirm nahi hui. Channel join karke dobara try karo.')
        return
    if not await force_gate(update, context): return
    if q.data == 'plans':
        kb=InlineKeyboardMarkup([[InlineKeyboardButton('7 Days — ₹99', callback_data='buy:7d')],[InlineKeyboardButton('28 Days — ₹299', callback_data='buy:28d')],[InlineKeyboardButton('Lifetime — ₹599', callback_data='buy:life')]])
        await q.message.reply_text('Premium plan select karo:', reply_markup=kb); return
    if q.data == 'myplan':
        await q.message.reply_text('Lifetime Premium' if is_premium(q.from_user.id) else ('Premium active hai.' if is_premium(q.from_user.id) else 'Abhi active Premium nahi hai. /start se plan choose karo.')); return
    if q.data.startswith('buy:'):
        plan=q.data.split(':',1)[1]
        if plan not in PLANS: return
        context.user_data['pending_plan']=plan
        name,price,_=PLANS[plan]
        text=f'Plan: {name}\nAmount: ₹{price}\n\nUPI ID: {UPI_ID}\n'
        if UPI_QR_URL: text += f'QR: {UPI_QR_URL}\n'
        text += '\nPayment karne ke baad apna UTR/transaction ID isi chat mein bhejo. Admin payment verify karke manually approve karega. UTR payment proof nahi hai—approval se pehle payment verify hogi.'
        await q.message.reply_text(text); return
    if q.data.startswith('approve:') or q.data.startswith('reject:'):
        if q.from_user.id != ADMIN_ID: await q.message.reply_text('Admin only.'); return
        action,pid=q.data.split(':'); pid=int(pid); c=db(); row=c.execute('SELECT user_id,plan,status FROM payments WHERE id=?',(pid,)).fetchone()
        if not row or row[2] != 'pending': c.close(); await q.message.reply_text('Payment not pending.'); return
        uid,plan,_=row
        if action=='approve':
            _,_,days=PLANS[plan]
            if days is None: c.execute('INSERT INTO users(user_id,premium_until,lifetime) VALUES(?,?,1) ON CONFLICT(user_id) DO UPDATE SET premium_until=NULL,lifetime=1',(uid,None))
            else:
                old=c.execute('SELECT premium_until FROM users WHERE user_id=?',(uid,)).fetchone()
                startat=datetime.now(timezone.utc)
                if old and old[0]:
                    try:
                        olddt=datetime.fromisoformat(old[0]); startat=max(startat,olddt)
                    except Exception: pass
                end=(startat+timedelta(days=days)).isoformat()
                c.execute('INSERT INTO users(user_id,premium_until,lifetime) VALUES(?,?,0) ON CONFLICT(user_id) DO UPDATE SET premium_until=excluded.premium_until,lifetime=0',(uid,end))
            c.execute('UPDATE payments SET status="approved" WHERE id=?',(pid,)); c.commit(); c.close()
            await context.bot.send_message(uid,'✅ Payment approved. Your Fire Extractor Premium is activated.')
            await q.message.reply_text(f'Approved payment #{pid}.')
        else:
            c.execute('UPDATE payments SET status="rejected" WHERE id=?',(pid,)); c.commit(); c.close()
            await context.bot.send_message(uid,'❌ Payment request rejected. If you believe this is a mistake, contact the admin.')
            await q.message.reply_text(f'Rejected payment #{pid}.')

async def receive_utr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await force_gate(update, context): return
    plan=context.user_data.get('pending_plan')
    if plan and update.message.text and len(update.message.text.strip()) >= 6:
        utr=update.message.text.strip()[:200]
        c=db(); cur=c.execute('INSERT INTO payments(user_id,plan,utr,status,created) VALUES(?,?,?,"pending",?)',(update.effective_user.id,plan,utr,datetime.now(timezone.utc).isoformat())); pid=cur.lastrowid; c.commit(); c.close()
        context.user_data.pop('pending_plan',None)
        await update.message.reply_text('🧾 UTR submit ho gaya. Admin payment verify karke approve karega.')
        kb=InlineKeyboardMarkup([[InlineKeyboardButton('✅ Approve', callback_data=f'approve:{pid}'),InlineKeyboardButton('❌ Reject',callback_data=f'reject:{pid}')]])
        await context.bot.send_message(ADMIN_ID, f'Payment request #{pid}\nUser: {update.effective_user.id}\nPlan: {PLANS[plan][0]} — ₹{PLANS[plan][1]}\nUTR: {utr}', reply_markup=kb)
        return
    await update.message.reply_text('Authorized TXT ya HTML file bhejo. Payment ke liye pehle /start → Buy Premium → plan choose karo.')

async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await force_gate(update, context): return
    if not is_premium(update.effective_user.id) and update.effective_user.id != ADMIN_ID:
        await update.message.reply_text('URL extraction ke liye active Premium chahiye. /start → Buy Premium.'); return
    doc=update.message.document
    if not doc or not (doc.file_name or '').lower().endswith(('.txt','.html','.htm')):
        await update.message.reply_text('Sirf .txt, .html ya .htm files support hoti hain.'); return
    if doc.file_size and doc.file_size > 10*1024*1024:
        await update.message.reply_text('Maximum file size 10 MB hai.'); return
    f=await context.bot.get_file(doc.file_id); path=f'input_{update.effective_user.id}_{doc.file_unique_id}.txt'; await f.download_to_drive(path)
    try:
        data=open(path,'r',encoding='utf-8',errors='ignore').read(); urls=list(dict.fromkeys(URL_RE.findall(data)))
        out=f'fire_extracted_{update.effective_user.id}.txt'
        with open(out,'w',encoding='utf-8') as w: w.write('\n'.join(urls) if urls else 'No URLs found.')
        await update.message.reply_document(out, caption=f'🔥 Fire Extractor — Found {len(urls)} URL(s)')
        os.remove(out)
    finally:
        if os.path.exists(path): os.remove(path)

async def status(update, context):
    if update.effective_user.id != ADMIN_ID: await update.message.reply_text('Admin only.'); return
    c=db(); users=c.execute('SELECT COUNT(*) FROM users').fetchone()[0]; pending=c.execute('SELECT COUNT(*) FROM payments WHERE status="pending"').fetchone()[0]; c.close()
    await update.message.reply_text(f'Users with plan records: {users}\nPending payments: {pending}')

def main():
    if not TOKEN: raise RuntimeError('Set BOT_TOKEN in Render Environment Variables')
    db(); app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start',start)); app.add_handler(CommandHandler('status',status))
    app.add_handler(CallbackQueryHandler(callback)); app.add_handler(MessageHandler(filters.Document.ALL,file_handler)); app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,receive_utr))
    app.run_polling(drop_pending_updates=True)
if __name__=='__main__': main()
