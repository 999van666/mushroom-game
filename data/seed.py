from database.database import Base, engine, SessionLocal
from database.models import Location, Mushroom

LOCATIONS = [
    ("🌳 Берёзовая роща", "Спокойный лес для начинающих грибников.", 1, 0),
    ("🌲 Смешанный лес", "Здесь встречаются более редкие находки.", 5, 2500),
    ("🌲 Старый бор", "Глубокий лес с шансом найти редкие грибы.", 10, 15000),
]

MUSHROOMS = [
("Сыроежка зелёная","common",18,30,180,3,3,1),
("Сыроежка пищевая","common",16,40,200,3,3,1),
("Опёнок осенний","common",15,30,160,4,4,1),
("Маслёнок обыкновенный","common",14,50,250,5,5,1),
("Моховик","common",12,50,300,5,5,1),
("Дождевик","common",10,30,250,4,4,1),
("Навозник","common",8,40,220,3,4,1),
("Свинушка","common",7,50,350,4,5,1),
("Волнушка","uncommon",7,50,300,8,10,1),
("Груздь","uncommon",6,80,500,10,12,1),
("Лисичка","uncommon",16,40,250,12,13,2),
("Подберёзовик","uncommon",15,80,600,13,15,2),
("Подосиновик","uncommon",14,80,700,15,17,2),
("Рядовка","uncommon",12,60,400,10,14,2),
("Ежовик гребенчатый","uncommon",10,50,400,18,20,2),
("Козляк","uncommon",8,60,450,16,18,2),
("Шампиньон лесной","uncommon",7,50,350,14,17,2),
("Трутовик","uncommon",6,100,800,12,20,2),
("Белый гриб","rare",5,100,1200,35,40,3),
("Польский гриб","rare",4,100,800,30,35,3),
("Дубовик","rare",3,100,900,32,38,3),
]

def seed():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        if db.query(Location).count() == 0:
            db.add_all([Location(name=n, description=d, required_level=l, unlock_price=p) for n,d,l,p in LOCATIONS])
            db.commit()
        if db.query(Mushroom).count() == 0:
            loc_ids = [x.id for x in db.query(Location).order_by(Location.id).all()]
            for name,rarity,chance,mn,mx,price,xp,loc_no in MUSHROOMS:
                db.add(Mushroom(name=name, rarity=rarity, chance=chance, min_weight=mn, max_weight=mx,
                                price_100g=price, xp=xp, location_id=loc_ids[loc_no-1]))
            db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
