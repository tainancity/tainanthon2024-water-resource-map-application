from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
import uvicorn
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from pydantic import BaseModel
import os

# 設定 FastAPI 應用程式
app = FastAPI()

# 資料庫連線設定 
host = os.getenv("DB_HOST", "127.0.0.1")
database = "postgres"
user = "postgres"
password = "admin"
port = "5432"
engine = create_async_engine(f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}", echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

# 請求單點模型
class PointRequest(BaseModel):
    longitude: float  # 經度
    latitude: float  # 緯度
    radius: float  # 單位為公尺
    overlap_ratio: float = Query(0.8, ge=0, le=1)  # 重疊面積比率門檻 超過此門檻才會被納入計算 預設為80%

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "longitude": 120.1854,
                    "latitude": 22.9921,
                    "radius": 500,
                    "overlap_ratio": 0.8
                }
            ]
        }
    }

# 請求多邊範圍模型
class PolygonRequest(BaseModel):
    wkt_polygon: str  # Well-Known Text 格式的多邊形 例如: POLYGON((x1 y1, x2 y2, x3 y3, x1 y1))
    overlap_ratio: float = Query(0.8, ge=0, le=1)  # 重疊面積比率門檻 超過此門檻才會被納入計算 預設為80%

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "wkt_polygon": "POLYGON((120.1828 22.9961, 120.1811 22.9869, 120.1906 22.9926, 120.1828 22.9961))",
                    "overlap_ratio": 0.8
                }
            ]
        }
    }

# 回傳家戶數模型
class HouseholdsResponse(BaseModel):
    households: int  # 家戶數量

# 回傳人口數模型
class PopulationResponse(BaseModel):
    population: int  # 人口數量

# 回傳面積模型
class AreaResponse(BaseModel):
    area: float  # 面積(平方米)

# 首頁
@app.get("/", response_class=HTMLResponse)
async def index():
    return '''
    <p>API測試請至此連結: <a href="http://127.0.0.1:8000/docs#/">http://127.0.0.1:8000/docs#/</a><p>
    '''


# 計算單點半徑範圍內家戶數
@app.post("/households/point", response_model=HouseholdsResponse)
async def get_households_within_radius(request: PointRequest):
    async with SessionLocal() as session:
        try:
            # 使用 PostGIS 查詢範圍內的戶數
            query = text("""       
                SELECT count(*) as households
                FROM households
                WHERE ST_DWithin(
                    geography(ST_SetSRID(ST_Point(:longitude, :latitude), 4326)),
                    geography(geometry),
                    :radius
                );
            """)
            result = await session.execute(query, {
                "longitude": request.longitude,
                "latitude": request.latitude,
                "radius": request.radius
            })
            data = result.fetchone()

            if data:
                return HouseholdsResponse(households=data.households or 0)
            else:
                raise HTTPException(status_code=404, detail="No data found within the specified radius")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


# 計算單點半徑範圍內人口數
@app.post("/population/point", response_model=PopulationResponse)
async def get_population_within_radius(request: PointRequest):
    async with SessionLocal() as session:
        try:
            # 使用 PostGIS 查詢範圍內的人口數
            query = text("""
                WITH 
                target_point AS (
                    SELECT ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326) AS geom
                ),
                buffered_area AS (
                    SELECT ST_Buffer(ST_Transform(geom, 3857), :radius) AS geom
                    FROM target_point
                )
                SELECT sum(population.p_cnt) as population
                FROM population
                JOIN buffered_area ON ST_Intersects(ST_Transform(population.geometry, 3857), buffered_area.geom)
                WHERE (ST_Area(ST_Intersection(ST_Transform(population.geometry, 3857), buffered_area.geom)) / ST_Area(ST_Transform(population.geometry, 3857))) >= :overlap_ratio;
            """)
            result = await session.execute(query, {
                "longitude": request.longitude,
                "latitude": request.latitude,
                "radius": request.radius,
                "overlap_ratio": request.overlap_ratio,
            })
            data = result.fetchone()

            if data:
                return PopulationResponse(population=data.population or 0)
            else:
                raise HTTPException(status_code=404, detail="No data found within the specified radius")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


# 計算單點半徑範圍內面積
@app.post("/area/point", response_model=AreaResponse)
async def get_area_within_radius(request: PointRequest):
    async with SessionLocal() as session:
        try:
            # 使用 PostGIS 查詢範圍內的戶數
            query = text("""       
                SELECT ST_Area(
                    ST_Buffer(
                        ST_SetSRID(ST_Point(:longitude, :latitude), 4326)::geography, 
                        :radius
                    )
                ) AS area;
            """)
            result = await session.execute(query, {
                "longitude": request.longitude,
                "latitude": request.latitude,
                "radius": request.radius
            })
            data = result.fetchone()

            if data:
                return AreaResponse(area=data.area or 0)
            else:
                raise HTTPException(status_code=404, detail="No data found within the specified radius")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        

# 計算多點面積範圍內家戶數
@app.post("/households/polygon", response_model=HouseholdsResponse)
async def get_households_within_polygon(request: PolygonRequest):
    async with SessionLocal() as session:
        try:
            # 使用 PostGIS 查詢範圍內的戶數
            query = text("""
                SELECT count(*) as households
                FROM households
                WHERE ST_Within(
                    geometry, 
                    ST_GeomFromText(:wkt_polygon, 4326));
            """)
            result = await session.execute(query, {
                "wkt_polygon": request.wkt_polygon,
            })
            data = result.fetchone()

            if data:
                return HouseholdsResponse(households=data.households or 0)
            else:
                raise HTTPException(status_code=404, detail="No data found within the specified area")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


# 計算多點面積範圍內人口數
@app.post("/population/polygon", response_model=PopulationResponse)
async def get_households_within_polygon(request: PolygonRequest):
    async with SessionLocal() as session:
        try:
            # 使用 PostGIS 查詢範圍內的人口數
            query = text("""
                WITH 
                input_polygon AS (
                    SELECT ST_SetSRID(ST_GeomFromText(:wkt_polygon), 4326) AS geom
                )
                SELECT sum(population.p_cnt) as population
                FROM population
                JOIN input_polygon ON ST_Intersects(ST_Transform(population.geometry, 3857), ST_Transform(input_polygon.geom, 3857))
                WHERE (ST_Area(ST_Intersection(ST_Transform(population.geometry, 3857), ST_Transform(input_polygon.geom, 3857))) / ST_Area(ST_Transform(population.geometry, 3857))) >= :overlap_ratio;
            """)
            result = await session.execute(query, {
                "wkt_polygon": request.wkt_polygon,
                "overlap_ratio": request.overlap_ratio,
            })
            data = result.fetchone()

            if data:
                return PopulationResponse(population=data.population or 0)
            else:
                raise HTTPException(status_code=404, detail="No data found within the specified area")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


# 計算多點面積範圍內面積
@app.post("/area/polygon", response_model=AreaResponse)
async def get_area_within_polygon(request: PolygonRequest):
    async with SessionLocal() as session:
        try:
            # 使用 PostGIS 查詢範圍內的戶數
            query = text("""
                SELECT ST_Area(
                    ST_Transform(
                        ST_GeomFromText(
                            :wkt_polygon, 
                            4326
                        ), 
                        32651
                    )
                ) AS area;
            """)
            result = await session.execute(query, {
                "wkt_polygon": request.wkt_polygon,
            })
            data = result.fetchone()

            if data:
                return AreaResponse(area=data.area or 0)
            else:
                raise HTTPException(status_code=404, detail="No data found within the specified area")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        

# 主程式
if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
