# app/models.py
from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime

class HisseVeri(BaseModel):
    kod: str
    fiyat: float
    hedef_fiyat: Optional[float] = None
    potansiyel_getiri: Optional[float] = None
    direnc1: Optional[float] = None
    direnc2: Optional[float] = None
    hisse_puani: Optional[int] = None

class Bilanco(BaseModel):
    kod: str
    net_kar: float = 0
    favok: float = 0
    ciro: float = 0
    borc: float = 0
    net_nakit: float = 0
    ozsermaye: float = 0

class AnalizSonucu(BaseModel):
    kod: str
    fiyat: float
    hedef_fiyat: float
    ucuzluk_skoru: int
    teknik_skoru: int
    kalite_skoru: int
    katalizor_skoru: int
    toplam_skor: int
    potansiyel_getiri: float
    tarih: datetime
