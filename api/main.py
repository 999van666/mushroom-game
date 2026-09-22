import random
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database.database import Base, engine, get_db
from database.models import User, Mushroom, Location, Catch

Base.metadata.create_all(engine)
app = FastAPI(title="🍄 Грибалка API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
RARITY_NAMES={"common":"🟢 Обычный","uncommon":"🔵 Необычный","rare":"🟣 Редкий"}
QUALITY=[("🥀 Плохое",10,.60),("⚪ Обычное",55,1),("🟢 Хорошее",25,1.25),("🔵 Отличное",8,1.7),("🟣 Идеальное",2,3)]
class SearchRequest(BaseModel):
    telegram_id:int
    first_name:str="Грибник"
    username:str|None=None
    location_id:int=1
    mode:str="quick"

def restore_energy(user):
    now=datetime.utcnow(); elapsed=now-user.last_energy_update
    units=int(elapsed.total_seconds()//300)
    if units>0:
        user.energy=min(user.max_energy,user.energy+units)
        user.last_energy_update += timedelta(minutes=5*units)

def get_user(db, telegram_id, first_name="Грибник", username=None):
    u=db.query(User).filter(User.telegram_id==telegram_id).first()
    if not u:
        u=User(telegram_id=telegram_id,first_name=first_name or "Грибник",username=username)
        db.add(u); db.commit(); db.refresh(u)
    else:
        if first_name: u.first_name=first_name
        if username is not None: u.username=username
    restore_energy(u); db.commit(); return u

def add_xp(u, amount):
    u.xp += amount
    while u.level<100 and u.xp >= 100*u.level*u.level:
        u.level += 1

@app.get("/api/health")
def health(): return {"ok":True,"game":"mushroom-game"}

@app.get("/api/user/{telegram_id}")
def user_info(telegram_id:int, db:Session=Depends(get_db)):
    u=get_user(db,telegram_id)
    return {"id":u.id,"telegram_id":u.telegram_id,"first_name":u.first_name,"level":u.level,"xp":u.xp,"coins":u.coins,"energy":u.energy,"max_energy":u.max_energy,"basket_capacity":u.basket_capacity,"total_weight":round(u.total_weight,1)}

@app.get("/api/locations/{telegram_id}")
def locations(telegram_id:int, db:Session=Depends(get_db)):
    u=get_user(db,telegram_id); out=[]
    for l in db.query(Location).filter(Location.active==True).order_by(Location.id):
        unlocked=(l.id==1 or u.level>=l.required_level)
        out.append({"id":l.id,"name":l.name,"description":l.description,"required_level":l.required_level,"unlock_price":l.unlock_price,"unlocked":unlocked})
    return out

@app.post("/api/search")
def search(req:SearchRequest, db:Session=Depends(get_db)):
    u=get_user(db,req.telegram_id,req.first_name,req.username)
    l=db.query(Location).filter(Location.id==req.location_id,Location.active==True).first()
    if not l: raise HTTPException(404,"Локация не найдена")
    if u.level<l.required_level: raise HTTPException(400,"Локация ещё не открыта")
    cost={"quick":1,"careful":2,"expedition":5}.get(req.mode)
    if cost is None: raise HTTPException(400,"Неизвестный режим поиска")
    if u.energy<cost: raise HTTPException(400,"Недостаточно энергии")
    mushrooms=db.query(Mushroom).filter(Mushroom.location_id==l.id,Mushroom.active==True).all()
    if not mushrooms: raise HTTPException(500,"В локации нет грибов")
    if u.total_weight >= u.basket_capacity: raise HTTPException(400,"Корзина заполнена")
    u.energy-=cost
    weights=[]
    for m in mushrooms:
        w=m.chance
        if req.mode=="careful" and m.rarity=="rare": w*=1.25
        if req.mode=="expedition" and m.rarity=="rare": w*=1.5
        weights.append(w)
    m=random.choices(mushrooms,weights=weights,k=1)[0]
    weight=random.randint(m.min_weight,m.max_weight)
    quality,_,mult=random.choices(QUALITY,weights=[q[1] for q in QUALITY],k=1)[0]
    available_grams=max(0,(u.basket_capacity-u.total_weight)*1000)
    weight=min(weight,available_grams)
    if weight<1: raise HTTPException(400,"В корзине недостаточно места")
    price=max(1,round(weight/100*m.price_100g*mult)); xp=m.xp
    before=db.query(Catch).filter(Catch.user_id==u.id).count()
    u.total_weight+=weight/1000; add_xp(u,xp)
    db.add(Catch(user_id=u.id,mushroom_id=m.id,location_id=l.id,weight=weight,quality=quality,price=price,xp=xp))
    db.commit()
    return {"mushroom":m.name,"rarity":RARITY_NAMES.get(m.rarity,m.rarity),"quality":quality,"weight":weight,"price":price,"xp":xp,"level":u.level,"energy":u.energy,"total_weight":round(u.total_weight,1),"new_find":before==0}

@app.get("/api/inventory/{telegram_id}")
def inventory(telegram_id:int,db:Session=Depends(get_db)):
    u=get_user(db,telegram_id); cs=db.query(Catch).filter(Catch.user_id==u.id,Catch.sold==False).all(); items=[]
    for c in cs:
        m=db.query(Mushroom).filter(Mushroom.id==c.mushroom_id).first()
        items.append({"id":c.id,"name":m.name,"rarity":m.rarity,"weight":c.weight,"quality":c.quality,"price":c.price})
    return {"items":items,"total_weight":round(u.total_weight,1),"capacity":u.basket_capacity}

@app.post("/api/sell-all/{telegram_id}")
def sell_all(telegram_id:int,db:Session=Depends(get_db)):
    u=get_user(db,telegram_id); cs=db.query(Catch).filter(Catch.user_id==u.id,Catch.sold==False).all(); total=sum(c.price for c in cs)
    for c in cs: c.sold=True
    u.coins+=total; u.total_weight=0; db.commit()
    return {"sold":len(cs),"coins":total,"balance":u.coins}

@app.get("/api/leaderboard")
def leaderboard(db:Session=Depends(get_db)):
    us=db.query(User).order_by(User.level.desc(),User.xp.desc()).limit(20).all()
    return [{"place":i+1,"name":u.first_name,"level":u.level,"xp":u.xp} for i,u in enumerate(us)]
app.mount("/", StaticFiles(directory="webapp", html=True), name="webapp")