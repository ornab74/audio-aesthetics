"""Stripe subscription gateway. Nothing charges money until Stripe keys are configured.
Local/FOSS audio analysis never uses billing or networking.
"""
from __future__ import annotations
import hashlib,os,secrets,sqlite3
from pathlib import Path
from fastapi import HTTPException

def _db():
    dest=Path(os.getenv('AESTHETICS_DB','./aesthetics_billing.sqlite3')).expanduser()
    dest.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(dest,timeout=20)
    db.execute('''CREATE TABLE IF NOT EXISTS licenses (
      subscription_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL,
      token_hash TEXT UNIQUE, status TEXT NOT NULL DEFAULT 'incomplete')''')
    db.commit();return db

def _stripe():
    try:import stripe
    except ImportError:raise HTTPException(503,'Install Stripe SDK: pip install stripe')
    if not os.getenv('STRIPE_SECRET_KEY'):raise HTTPException(503,'Stripe is not configured')
    stripe.api_key=os.environ['STRIPE_SECRET_KEY']
    return stripe

def active(token:str|None)->bool:
    if not token:return False
    hashed=hashlib.sha256(token.encode()).hexdigest()
    with _db() as db:
        found=db.execute('SELECT 1 FROM licenses WHERE token_hash=? AND status IN (\'active\',\'trialing\')',(hashed,)).fetchone()
    return bool(found)

def checkout(email:str)->str:
    stripe=_stripe();price=os.getenv('STRIPE_PRICE_ID')
    if not price:raise HTTPException(503,'Recurring Stripe Price ID not configured')
    configured=stripe.Price.retrieve(price)
    recurring=getattr(configured,'recurring',None) or {}
    interval=recurring.get('interval') if isinstance(recurring,dict) else getattr(recurring,'interval',None)
    if configured.currency.lower()!='usd' or configured.unit_amount!=2000 or interval!='month':
        raise HTTPException(503,'Stripe Price must be USD $20.00 charged monthly')
    base=os.getenv('PUBLIC_BASE_URL','http://127.0.0.1:8788').rstrip('/')
    if not (base.startswith('https://') or base.startswith('http://127.0.0.1:')):
        raise HTTPException(503,'PUBLIC_BASE_URL must use HTTPS outside localhost')
    session=stripe.checkout.Session.create(
        mode='subscription',line_items=[{'price':price,'quantity':1}],customer_email=email,
        success_url=base+'/?session_id={CHECKOUT_SESSION_ID}',
        cancel_url=base+'/?canceled=1',
        allow_promotion_codes=True)
    return session.url

def activate(session_id:str)->str:
    if not (session_id.startswith('cs_') and len(session_id)<256):raise HTTPException(400,'Invalid checkout session')
    stripe=_stripe();s=stripe.checkout.Session.retrieve(session_id)
    if s.mode!='subscription' or s.status!='complete' or not s.subscription or not s.customer:
        raise HTTPException(403,'Checkout is not complete')
    sub=stripe.Subscription.retrieve(s.subscription)
    if sub.status not in ('active','trialing'):
        raise HTTPException(403,'Subscription is not active')
    with _db() as db:
        row=db.execute('SELECT token_hash FROM licenses WHERE subscription_id=?',(s.subscription,)).fetchone()
        # Never rotate/reveal an already-issued license based on a reusable Checkout Session URL.
        if row and row[0]:raise HTTPException(409,'License already activated. Contact support for recovery.')
        secret='ae_'+secrets.token_urlsafe(36)
        hashed=hashlib.sha256(secret.encode()).hexdigest()
        db.execute('''INSERT INTO licenses(subscription_id,customer_id,token_hash,status)
                   VALUES(?,?,?,?) ON CONFLICT(subscription_id) DO UPDATE SET
                   token_hash=excluded.token_hash,status=excluded.status''',
                   (s.subscription,s.customer,hashed,sub.status));db.commit()
    return secret

def customer_for(token):
    if not active(token):raise HTTPException(403,'Active Pro subscription required')
    with _db() as db:
        row=db.execute('SELECT customer_id FROM licenses WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
    if not row:raise HTTPException(403,'Unknown license')
    return row[0]

def portal(token):
    stripe=_stripe();customer=customer_for(token)
    base=os.getenv('PUBLIC_BASE_URL','http://127.0.0.1:8788').rstrip('/')
    session=stripe.billing_portal.Session.create(customer=customer,return_url=base)
    return session.url

def webhook(body:bytes,signature:str):
    stripe=_stripe();secret=os.getenv('STRIPE_WEBHOOK_SECRET')
    if not secret:raise HTTPException(503,'Stripe webhook secret not configured')
    try:event=stripe.Webhook.construct_event(body,signature,secret)
    except Exception:raise HTTPException(400,'Invalid Stripe signature')
    typ=event['type'];obj=event['data']['object']
    if typ=='checkout.session.completed':
        sid=obj.get('subscription');cid=obj.get('customer')
        if sid and cid:
            with _db() as db:
                db.execute('INSERT OR IGNORE INTO licenses(subscription_id,customer_id,status) VALUES(?,?,?)',(sid,cid,'incomplete'));db.commit()
    if typ in ('customer.subscription.updated','customer.subscription.deleted'):
        with _db() as db:
            db.execute('UPDATE licenses SET status=? WHERE subscription_id=?',(obj.get('status','canceled'),obj['id']));db.commit()
    if typ=='invoice.payment_failed':
        sid=obj.get('subscription')
        if sid:
            with _db() as db:
                db.execute('UPDATE licenses SET status=? WHERE subscription_id=?',('past_due',sid));db.commit()
    return {'received':True}
