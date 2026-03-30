from sqlalchemy import Column, BigInteger, Integer, String, Text, Numeric
from database.session import Base

class MenuItem(Base):
    __tablename__ = "menu_item"

    item_id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    category_id = Column(BigInteger, nullable=True)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    is_chef_recommend = Column(Integer, nullable=True)
    name = Column(String(255), nullable=False)
    price = Column(Numeric(10, 2), nullable=True)
    subcategory_id = Column(BigInteger, nullable=True)