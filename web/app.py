import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, ALL, dcc, html, dash_table
import dash_leaflet as dl
from dash_extensions.javascript import assign
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon
from shapely import wkt
import requests
import os

# API主機位置
api_server = os.getenv("API_HOST", "127.0.0.1")
api_port = 8000


app = dash.Dash(
    title='地圖範圍標記資訊工具',
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP],
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"}
    ],
    suppress_callback_exceptions=True,
)
server = app.server

app.layout = dbc.Container([

    dbc.Row([
        html.H2(html.Center("地圖範圍標記資訊工具")),
    ], className="mt-3 mb-3"),

    dbc.Row([

        dbc.Col([

            dbc.Label('請輸入資料集名稱:'),
            dbc.Input(id="dataset-name", type="text"),
        ], md=4),

    ], className="mb-3"),

    html.Hr(),

    dbc.Row([

        dbc.Col([
            html.Label(f"欄位名稱:"),
        ], md=4),

        dbc.Col([
            html.Label(f"資料型別:"),
        ], md=4),
    ], className="mb-3"),

    # 自定義欄位名稱設定
    html.Div(id='custom-name-options'), 

    dbc.Row([
    
        dbc.Col([

            dbc.Button("加入新欄位", id="add-input-btn", color="primary", n_clicks=0),
        ], md=4),
    ], className="mb-3"),

    html.Hr(),

    dbc.Row([

        # 地圖放置位置
        dbc.Col([
            dl.Map(
                center=[23.1417, 120.2513],
                zoom=11,
                children=[
                    dl.TileLayer(),  # 基礎地圖
                    dl.FeatureGroup([
                        # 開啟地圖編輯控制
                        dl.EditControl(
                            id="edit-control", 
                            draw={
                                'marker': False, 
                                'polygon': True,  # 指開啟多邊形繪製功能
                                'polyline': False, 
                                'rectangle': False, 
                                'circle': False, 
                                'circlemarker': False,
                            },
                        ),  
                    ]),
                    dl.GeoJSON(id="geojson", zoomToBounds=False),
                ],
                id="map",
                style={'height': '70vh', 'width': '100%'},
            ),
        ], md=8),

        # 標註表格放置位置
        dbc.Col([

            dbc.Row([
                dbc.Col([
                    dbc.Label('經緯度範圍(polygon):'),
                    dbc.Input(id="data-polygon", type="text", disabled=True, placeholder='請於左側地圖標記範圍(必填 | 只能接受1個範圍)'),
                ]),
            ], className="mb-3"),

            dbc.Row([
                dbc.Col([
                    dbc.Label('面積範圍(平方公尺)(area):'),
                    dbc.Input(id="data-area", type="number", disabled=True, placeholder='程式自動依標記範圍計算'),
                ]),
            ], className="mb-3"),

            dbc.Row([
                dbc.Col([
                    dbc.Label('門牌數(households):'),
                    dbc.Input(id="data-households", type="number", disabled=True, placeholder='程式自動依標記範圍計算'),
                ]),
            ], className="mb-3"),

            dbc.Row([
                dbc.Col([
                    dbc.Label('人口數(population):'),
                    dbc.Input(id="data-population", type="number", disabled=True, placeholder='程式自動依標記範圍計算'),
                ]),
            ], className="mb-3"),

            html.Div(id='custom-inputs'),

            dbc.Row([
                dbc.Col([
                    dbc.Button("新增資料", id="insert-data-button", n_clicks=0, color="primary", style={"margin-top": "30px"}),
                ]),
            ], className="mb-3"),

            dbc.Row([
                dbc.Col([
                    html.Div(id="error-message"),
                ]),

            ], className="mb-3"),
        ]),
    ], className="mb-3"),

    html.Hr(),

    dbc.Row([

        # 呈現當前標註結果
        dbc.Col([
            html.Div(id="dataset-table-div"),
        ]),

    ], className="mb-3"),

    # 資料下載按鈕
    html.Div(id="download-data-component"),

    # 暫存資料表
    dcc.Store(id='store-data', data=pd.DataFrame().to_dict('records')),
    # 下載CSV格式檔案資料
    dcc.Download(id="download-csv-data"),
    # 下載GeoJson格式檔案資料
    dcc.Download(id="download-geojson-data"),

])


# 依使用者需求產生自定義欄位
@app.callback(
    Output("custom-name-options", "children"),
    Input("add-input-btn", "n_clicks"),
    State("custom-name-options", "children")
)
def add_input_fields(n_clicks, existing_children):

    if existing_children is None:
        existing_children = []

    new_field = dbc.Row([
        dbc.Col([
            dbc.Input(
                id={'type': 'custom-input', 'index': n_clicks},
                type='text',
                placeholder=f"請輸入新欄位名稱",
            ),
        ], md=4),
        dbc.Col([
            dbc.Select(
                id={'type': 'custom-input-type', 'index': n_clicks},
                options=[
                    {'label': '文字', 'value': 'text'},
                    {'label': '數值', 'value': 'number'}
                ],
                value='text',
            ),
        ], md=4),
    ], className="mb-3")

    return existing_children + [new_field]


# 依據欄位名稱生成對應的輸入框
@app.callback(
    Output('custom-inputs', 'children'),
    Input({'type': 'custom-input', 'index': ALL}, 'value'),
    Input({'type': 'custom-input-type', 'index': ALL}, 'value'),
)
def generate_inputs(field_name, field_type):

    outputs = []
    for i, (field_name, field_type) in enumerate(zip(field_name, field_type)):
        if field_name:
            outputs.extend([
                dbc.Row([
                    dbc.Col([
                        html.Label(
                            id={'type': 'field-label', 'index': i+1}, 
                            children=f"{field_name}:"
                            ),
                        dbc.Input(
                            id={'type': 'field-input', 'index': i+1}, 
                            type=field_type, 
                            placeholder=f"請輸入{'文字' if field_type == 'text' else '數值'}"
                            )
                    ]),
                ], className="mb-3"),  
            ])

    return outputs


# 處理使用者地圖標記多邊形
@app.callback(
        Output("geojson", "data"), 
        Output("data-polygon", "value"),
        Output('data-households', 'value'),
        Output('data-population', 'value'),
        Output('data-area', 'value'),
        Input("edit-control", "geojson")
)
def get_polygon(x):

    # 取出使用者標記的經緯度範圍，如果沒有資料則設為空列表
    coordinates = [elem['geometry']['coordinates'] for elem in x.get('features', [])] if x else []

    if coordinates:

        # 只取第一個多邊形的外圍邊界
        outer_boundary = coordinates[0][0] if isinstance(coordinates[0], list) else []

        # 確保外圍邊界是正確格式並創建多邊形
        if outer_boundary and isinstance(outer_boundary[0], list):
            polygon = Polygon(outer_boundary)
            wkt = polygon.wkt
        else:
            wkt = None
    else:
        wkt = None

    households = None
    population = None
    area = None
    if wkt:

        # 取得使用者選取範圍內的家戶數
        url = f'http://{api_server}:{api_port}/households/polygon'
        data = {
            'wkt_polygon': wkt
        }
        response = requests.post(url, json=data)
        if response.status_code == 200:
            households = response.json()['households']

        # 取得使用者選取範圍內的人口數
        url = f'http://{api_server}:{api_port}/population/polygon'
        data = {
            'overlap_ratio': 0.5,
            'wkt_polygon': wkt
        }
        response = requests.post(url, json=data)
        if response.status_code == 200:
            population = response.json()['population']

        # 取得使用者選取範圍的面積
        url = f'http://{api_server}:{api_port}/area/polygon'
        data = {
            'wkt_polygon': wkt
        }
        response = requests.post(url, json=data)
        if response.status_code == 200:
            area = round(response.json()['area'], 2)

    return x, wkt, households, population, area


# 使用者新增資料
@app.callback(
    Output('error-message', 'children'),
    Output('dataset-table-div', 'children'),
    Output('store-data', 'data'),
    Output("edit-control", "editToolbar"),
    Output("download-data-component", "children"),
    Output({'type': 'field-input', 'index': ALL}, 'value'),
    Input("insert-data-button", "n_clicks"),
    State('store-data', 'data'),
    State({'type': 'field-label', 'index': ALL}, 'children'),
    State({'type': 'field-input', 'index': ALL}, 'value'),
    State('data-polygon', 'value'),
    State('data-area', 'value'),
    State('data-households', 'value'),
    State('data-population', 'value'),
)
def insert_data(n_clicks, data, field_label, field_value, data_polygon, data_area, data_households, data_population):

    # 初始輸出值
    dataset_table = None
    updated_data = pd.DataFrame(data)
    downloadDataComponent = []
    errorMessage = []

    # 按鈕需被點擊 且需要有效的 polygon 資料才會被新增
    if n_clicks and data_polygon:

        # 使用者自定義資料
        customData = {label[:-1]: value for label, value in zip(field_label, field_value)}

        # 將新增資料封裝為 DataFrame
        new_data = pd.DataFrame([{
            **customData,
            'polygon': data_polygon,
            'area': data_area,
            'households': data_households,
            'population': data_population,
        }])

        # 將新資料合併到現有資料中
        if data:
            existing_data = pd.DataFrame(data)
            updated_data = pd.concat([existing_data, new_data], ignore_index=True)
        else:
            updated_data = new_data

        # 產生下載按鈕
        downloadDataComponent = [
            dbc.Row([

                dbc.Col([
                    dbc.Button("下載CSV格式檔案", id="download-csv-button", n_clicks=0, color="primary", style={"margin-top": "30px"}),
                    dbc.Button("下載GeoJSON格式檔案", id="download-geojson-button", n_clicks=0, color="primary", style={"margin-top": "30px"}),
                ], style={
                    "display": "flex",
                    "gap": "10px",  # 按鈕之間的間距
                    "margin-top": "30px",
                },),

            ], className="mb-3")
        ]

    # 提示訊息
    if n_clicks and not data_polygon:
        errorMessage = errorMessage + [html.Span('提示訊息: 請記得在地圖上框選範圍唷!', style={'color': 'red'})]
        
    # 更新表格顯示
    if len(updated_data) > 0:

        dataset_table = [
            html.H2(html.Center('目前標記資料')),
            dash_table.DataTable(
                id='dataset-table',
                data=updated_data.to_dict('records'),
                columns=[{"name": col, "id": col}  for col in updated_data.columns],
                style_cell={
                    'maxWidth': '100px', 'textOverflow': 'ellipsis'
                },
                editable=True,  # 允許編輯內容
                row_deletable=True,  # 允許刪除列
                markdown_options={"html": True},
            ),
        ]

    return [
        errorMessage,
        dataset_table, 
        updated_data.to_dict('records') if updated_data is not None else None, 
        dict(mode="remove", action="clear all", n_clicks=n_clicks),  # 清除目前地圖標記
        downloadDataComponent,
        [""] * len(field_value),
    ]


# 下載CSV格式資料
@app.callback(
    Output("download-csv-data", "data"),
    Input("download-csv-button", "n_clicks"),
    State('dataset-name', 'value'),
    State('store-data', 'data'),
)
def download_csv(n_clicks, datasetName, data):
    
    if n_clicks > 0:
        df = pd.DataFrame(data).to_csv(encoding='utf-8-sig', index=False)
        return dcc.send_bytes(df.encode(), f"{datasetName}.csv")


# 下載GeoJSON格式資料
@app.callback(
    Output("download-geojson-data", "data"),
    Input("download-geojson-button", "n_clicks"),
    State('dataset-name', 'value'),
    State('store-data', 'data'),
)
def download_geojson(n_clicks, datasetName, data):

    if n_clicks > 0:
        df = pd.DataFrame(data)
        # 使用 WKT (Well-Known Text) 將 polygon 字串轉換為 Shapely Geometry 物件
        df['polygon'] = df['polygon'].apply(wkt.loads)
        # 使用 GeoPandas 將 DataFrame 轉換為 GeoDataFrame
        df = gpd.GeoDataFrame(df, geometry='polygon')
        df = df.to_json()
        return dcc.send_bytes(df.encode(), f"{datasetName}.geojson")


# 主程式
if __name__ == "__main__":
    app.run_server(host='0.0.0.0', port=8888, debug=True)