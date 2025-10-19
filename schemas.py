from typing import Any, List, Optional

from pydantic import BaseModel

# TODO: later we should look about the filed types cus they could be wrong i test it on some samples but that wont garantee it


class InstrumentState(BaseModel):
    idn: int
    dEven: int
    hEven: int
    insCode: Optional[str] = None
    lVal18AFC: Optional[str] = None
    lVal30: Optional[str] = None
    cEtaval: str
    realHeven: int
    underSupervision: int
    cEtavalTitle: str


class ClosingPriceInfo(BaseModel):
    instrumentState: InstrumentState
    instrument: Optional[Any] = None
    thirtyDayClosingHistory: Optional[Any] = None
    lastHEven: int
    finalLastDate: int
    dEven: int
    hEven: int
    pClosing: float
    priceChange: float
    priceMin: float
    priceMax: float
    priceYesterday: float
    priceFirst: float
    pDrCotVal: float
    zTotTran: float
    qTotTran5J: float
    qTotCap: float
    nvt: float
    mop: int
    pRedTran: float
    last: bool
    iClose: bool
    yClose: bool
    id: int
    insCode: str


class BestLimit(BaseModel):
    number: int
    qTitMeDem: int
    zOrdMeDem: int
    pMeDem: float
    pMeOf: float
    zOrdMeOf: int
    qTitMeOf: int
    title: Optional[str] = None
    insCode: Optional[str] = None


class BestLimitsResponse(BaseModel):
    bestLimits: List[BestLimit]


class Trade(BaseModel):
    insCode: Optional[str] = None
    dEven: int
    nTran: int
    hEven: int
    qTitTran: int
    pTran: float
    qTitNgJ: int
    iSensVarP: str
    pPhSeaCotJ: float
    pPbSeaCotJ: float
    iAnuTran: int
    xqVarPJDrPRf: float
    canceled: int


class TradeResponse(BaseModel):
    trade: List[Trade]


class ClosingPriceResponse(BaseModel):
    closingPriceInfo: ClosingPriceInfo


class MarketWatchBestLimit(BaseModel):
    n: int
    qmd: int
    zmd: int
    pmd: float
    pmo: float
    zmo: int
    qmo: int
    rid: int


class MarketWatchItem(BaseModel):
    lva: str
    lvc: str
    eps: float
    pe: Optional[Any] = None
    pmd: float
    pmo: float
    qtj: float
    pdv: float
    ztt: float
    qtc: float
    bv: float
    pc: float
    pcpc: float
    pmn: float
    pmx: float
    py: float
    pf: float
    pcl: float
    vc: int
    csv: str
    insID: str
    pMax: float
    pMin: float
    ztd: float
    blDs: List[MarketWatchBestLimit]
    id: int
    insCode: str
    dEven: int
    hEven: int
    pClosing: float
    iClose: bool
    yClose: bool
    pDrCotVal: float
    zTotTran: float
    qTotTran5J: float
    qTotCap: float


class MarketWatchResponse(BaseModel):
    marketwatch: List[MarketWatchItem]


class PriceResponse(BaseModel):
    pDrCotVal: float
