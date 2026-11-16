import dash
from dash import html, dcc
from dash.dependencies import Input, Output
from dash import dash_table
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# -------------------------------------------------------------
# LOAD DATA
# -------------------------------------------------------------
df = pd.read_csv("bolas_de_ouro_futebol.csv")
df.columns = df.columns.str.strip()
df["ano"] = df["ano"].astype(int)

# Filtrar apenas os anos em que o prémio foi atribuído (exclui 2020)
df_valid = df[df["atribuido"] == True].copy()
countries = sorted(df_valid["pais_atual"].dropna().unique())

# -------------------------------------------------------------
# CREATE DASH APP
# -------------------------------------------------------------
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# -------------------------------------------------------------
# LAYOUT
# -------------------------------------------------------------
app.layout = html.Div([
    html.H1("Bolas de Ouro de Futebol Dashboard (1956–2024)", style={"textAlign": "center"}),

    dcc.Tabs(id="mainTabs", value="overviewTab", children=[
        dcc.Tab(label="Overview", value="overviewTab"),
        dcc.Tab(label="Graphics (Nested Tabs)", value="graphicsTab"),
        dcc.Tab(label="Data Table", value="tableTab"),
        dcc.Tab(label="Summary Statistics", value="summaryTab"),
    ]),

    html.Hr(),

    # ------------------- FILTERS -------------------
    html.Div([
        html.Div([
            html.Label("Select Country:"),
            dcc.Dropdown(
                id="countryFilter",
                options=[{"label": "All", "value": "All"}] + [{"label": c, "value": c} for c in countries],
                value=["All"],
                multi=True,
                style={"width": "95%"}
            )
        ], style={"width": "28%", "display": "inline-block"}),

        html.Div([
            html.Label("Select Year Range:"),
            dcc.RangeSlider(
                id="yearFilter",
                min=int(df_valid["ano"].min()),
                max=int(df_valid["ano"].max()),
                value=[int(df_valid["ano"].min()), int(df_valid["ano"].max())],
                marks={y: str(y) for y in range(int(df_valid["ano"].min()), int(df_valid["ano"].max()) + 1, 8)},
                tooltip={"placement": "bottom", "always_visible": True}
            )
        ], style={"width": "68%", "display": "inline-block", "paddingLeft": "2%"})
    ], style={"padding": "15px"}),

    html.Hr(),

    html.Div(id="tabContent"),
    dcc.Store(id="filteredData")
])

# -------------------------------------------------------------
# CALLBACK -> FILTER DATA
# -------------------------------------------------------------
@app.callback(
    Output("filteredData", "data"),
    [Input("countryFilter", "value"),
     Input("yearFilter", "value")]
)
def filter_data(countrysel, yearrange):
    low, high = yearrange
    dff = df_valid.copy()

    if countrysel and "All" not in countrysel:
        dff = dff[dff["pais_atual"].isin(countrysel)]

    dff = dff[(dff["ano"] >= low) & (dff["ano"] <= high)]
    return dff.to_dict("records")

# -------------------------------------------------------------
# CALLBACK -> MAIN TABS
# -------------------------------------------------------------
@app.callback(
    Output("tabContent", "children"),
    [Input("mainTabs", "value"),
     Input("filteredData", "data")]
)
def render_tabs(tab, data):
    if not data:
        return html.Div("No data available for the selected filters.")

    dff = pd.DataFrame(data)

    if tab == "overviewTab":
        dff_sorted = dff.sort_values("ano").copy()
        dff_sorted["trofeus_acumulados"] = dff_sorted.groupby("pais_atual").cumcount() + 1

        fig = go.Figure()
        for country in sorted(dff_sorted["pais_atual"].unique()):
            df_c = dff_sorted[dff_sorted["pais_atual"] == country]
            fig.add_trace(go.Scatter(
                x=df_c["ano"],
                y=df_c["trofeus_acumulados"],
                mode="lines+markers",
                name=country,
                text=df_c["jogador"] + " (" + df_c["clube"] + ")",
                hovertemplate="<b>%{fullData.name}</b><br>Ano: %{x}<br>Acumulado: %{y}<br>Vencedor: %{text}<extra></extra>"
            ))

        fig.update_layout(
            title="Evolução Acumulada de Bolas de Ouro por País",
            xaxis_title="Ano",
            yaxis_title="Total Acumulado de Troféus"
        )

        return html.Div([
            html.H3("Overview"),
            dcc.Graph(figure=fig)
        ])

    if tab == "graphicsTab":
        return html.Div([
            dcc.Tabs(id="nestedTabs", value="bar", children=[
                dcc.Tab(label="Bar Chart (By Country)", value="bar"),
                dcc.Tab(label="Cumulative Line Chart", value="line"),
                dcc.Tab(label="Scatter Plot (Winners Timeline)", value="scatter"),
                dcc.Tab(label="Trendline Plot (Cumulative)", value="trend")
            ]),
            html.Div(id="nestedContent", style={"paddingTop": "20px"})
        ])

    if tab == "tableTab":
        cols_display = ["ano", "jogador", "pais_atual", "pais", "clube"]
        return html.Div([
            html.H3("Filtered Data Table"),
            dash_table.DataTable(
                columns=[{"name": col, "id": col} for col in cols_display],
                data=dff[cols_display].to_dict("records"),
                page_size=15,
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "center"}
            )
        ])

    if tab == "summaryTab":
        resumo_pais = (
            dff.groupby("pais_atual")
            .agg(
                Total_Bolas_de_Ouro=("ano", "count"),
                Primeiro_Titulo=("ano", "min"),
                Ultimo_Titulo=("ano", "max"),
                Jogadores_Distintos=("jogador", "nunique")
            )
            .sort_values(by="Total_Bolas_de_Ouro", ascending=False)
        )
        return html.Div([
            html.H3("Summary Statistics by Country"),
            html.Pre(resumo_pais.to_string())
        ])

# -------------------------------------------------------------
# CALLBACK -> NESTED GRAPH TABS
# -------------------------------------------------------------
@app.callback(
    Output("nestedContent", "children"),
    [Input("nestedTabs", "value"),
     Input("filteredData", "data")]
)
def nested_graphs(nestedTab, data):
    if not data:
        return html.Div("Waiting for data...")

    dff = pd.DataFrame(data)
    dff_sorted = dff.sort_values("ano").copy()
    dff_sorted["trofeus_acumulados"] = dff_sorted.groupby("pais_atual").cumcount() + 1

    if nestedTab == "bar":
        sums = dff.groupby("pais_atual").size().reset_index(name="total_trofeus")
        sums = sums.sort_values("total_trofeus", ascending=False)
        fig = go.Figure(go.Bar(
            x=sums["pais_atual"],
            y=sums["total_trofeus"],
            text=sums["total_trofeus"],
            textposition="auto"
        ))
        fig.update_layout(
            title="Total de Bolas de Ouro por País",
            xaxis_title="País",
            yaxis_title="Número de Troféus"
        )
        return dcc.Graph(figure=fig)

    if nestedTab == "line":
        fig = go.Figure()
        for country in sorted(dff_sorted["pais_atual"].unique()):
            df_c = dff_sorted[dff_sorted["pais_atual"] == country]
            fig.add_trace(go.Scatter(
                x=df_c["ano"],
                y=df_c["trofeus_acumulados"],
                mode="lines+markers",
                name=country,
                text=df_c["jogador"]
            ))
        fig.update_layout(
            title="Evolução Acumulada por País",
            xaxis_title="Ano",
            yaxis_title="Troféus Acumulados"
        )
        return dcc.Graph(figure=fig)

    if nestedTab == "scatter":
        fig = go.Figure()
        for country in sorted(dff["pais_atual"].unique()):
            df_c = dff[dff["pais_atual"] == country]
            fig.add_trace(go.Scatter(
                x=df_c["ano"],
                y=df_c["pais_atual"],
                mode="markers",
                marker=dict(size=11),
                name=country,
                text=df_c["jogador"] + " (" + df_c["clube"] + ")",
                hovertemplate="<b>%{y}</b><br>Ano: %{x}<br>Vencedor: %{text}<extra></extra>"
            ))
        fig.update_layout(
            title="Linha Temporal de Conquistas por País",
            xaxis_title="Ano",
            yaxis_title="País"
        )
        return dcc.Graph(figure=fig)

    if nestedTab == "trend":
        fig = go.Figure()
        for country in sorted(dff_sorted["pais_atual"].unique()):
            df_c = dff_sorted[dff_sorted["pais_atual"] == country]
            fig.add_trace(go.Scatter(
                x=df_c["ano"],
                y=df_c["trofeus_acumulados"],
                mode="markers",
                name=country
            ))
            if len(df_c) > 1:
                m, b = np.polyfit(df_c["ano"], df_c["trofeus_acumulados"], 1)
                fig.add_trace(go.Scatter(
                    x=df_c["ano"],
                    y=m * df_c["ano"] + b,
                    mode="lines",
                    name=f"{country} trend"
                ))
        fig.update_layout(
            title="Tendência de Conquistas Acumuladas por País",
            xaxis_title="Ano",
            yaxis_title="Troféus Acumulados"
        )
        return dcc.Graph(figure=fig)

# -------------------------------------------------------------
# RUN APP
# -------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
