import streamlit as st
import pandas as pd
from pizza_gen import pizza_plot
import plotly.graph_objects as go
from plotly.colors import sample_colorscale
import re
def translate_weekday(day):
    match day:
        case "Monday":
            return "Segunda"
        case "Tuesday":
            return "Terca"
        case "Wednesday":
            return "Quarta"
        case "Thursday":
            return "Quinta"
        case "Friday":
            return "Sexta"
        case "Saturday":
            return "Sabado"
        case "Sunday":
            return "Domingo"
        case _:
            return day

def translate_month(month_name):
    match month_name:
        case 'January':
            return 'Jan'
        case 'February':
            return 'Fev'
        case 'March':
            return 'Mar'
        case 'April':
            return 'Abr'
        case 'May':
            return 'Mai'
        case 'June':
            return 'Jun'
        case 'July':
            return 'Jul'
        case 'August':
            return 'Ago'
        case 'September':
            return 'Set'
        case 'October':
            return 'Out'
        case 'November':
            return 'Nov'
        case 'December':
            return 'Dez'
        case _:
            return month_name

def format_label(row_tuple):
    row = row_tuple[1]
    month = translate_month(row['order_date'].month_name())
    day = row['order_date'].day
    weekday = translate_weekday(row['order_date'].day_name())

    return f"{day} de {month},\n{weekday}"


class ModeloCoocorrencia():
    def __init__(self, df):
        coocorrencias = dict()
        qtd_total = dict()
        preco_total = dict()
        for i, row in df.iterrows():
            ingredientes = row['pizza_ingredients'].split(", ")
            qtd = row['quantity']
            preco = row['total_price']
            peso = preco/(qtd*len(ingredientes))
            for ingrediente in ingredientes:
                qtd_total[ingrediente] = qtd_total.get(ingrediente, 0) + qtd
                preco_total[ingrediente] = preco_total.get(ingrediente, 0) + preco
                if coocorrencias.get(ingrediente, None) is None:
                    coocorrencias[ingrediente] = dict()
                hist = coocorrencias[ingrediente]
                for ingrediente_target in ingredientes:
                    hist[ingrediente_target] = hist.get(ingrediente_target, 0) + peso
        for ingrediente in coocorrencias.keys():
            hist = coocorrencias[ingrediente]
            fator_norm = hist[ingrediente]
            for ingrediente_target in hist.keys():
                hist[ingrediente_target] /= fator_norm

        self.coocorrencias = coocorrencias
        self.qtd_total = qtd_total
        self.preco_total = preco_total
    
    def top_k_sugestoes(self, k, ingredientes_selecionados):
        acumulado = dict()
        for ingrediente in ingredientes_selecionados:
            hist = self.coocorrencias[ingrediente]
            for ing_target, value in hist.items():
                acumulado[ing_target] = acumulado.get(ing_target, 0) + value
        for ingrediente in ingredientes_selecionados: acumulado.pop(ingrediente)
        return sorted(acumulado.keys(), key=lambda key : acumulado[key], reverse=True)[:k]


pizza_scaled_plot = lambda labels, values, extended_ratio=1.5 : (
    pizza_plot(labels, values, extended_ratio=extended_ratio,
        base_scale=st.session_state["pizza_scale"]
    )
)

@st.cache_data
def load_data(path="pizza_dataset.xlsx"):
    df = pd.read_excel(path)
    df['order_weekday'] = (df["order_date"].dt.day_name()
        .apply(translate_weekday)
    )
    df["pretty_date"] = list(map(format_label, df.iterrows()))
    return df

df = load_data()
weekdays_base = df[['order_date', 'order_weekday', 'quantity']].copy()
hour_base = df[['order_time', 'quantity']].copy()
hour_base['order_time'] = hour_base['order_time'].apply(lambda val: val.hour)

@st.cache_resource
def load_modelo(df):
    return ModeloCoocorrencia(df)

modelo_cooc = load_modelo(df)

st.set_page_config(layout="wide")

st.title("Dashboard da pizza")

tab1, tab2, tab3 = st.tabs(["Movimentação", "Popularidade", "Gerador de Pizza"])

def weekday_view(month_indexes, weekday_df = weekdays_base):
    weekdays = (weekday_df[weekday_df['order_date'].dt.month
        .isin(month_indexes)]
        .groupby("order_weekday")
        .sum(True)
        .sort_values('quantity', ascending=False)
    )
    return weekdays

def days_topN_view(month_indexes, N, weekday_df = weekdays_base):
    weekdays = (weekday_df[weekday_df['order_date'].dt.month
        .isin(month_indexes)]
        .groupby('order_date', as_index=False)
        .sum(True)
        .sort_values('quantity', ascending=False)
        .head(N)
    )
    weekdays["order_date"] = list(map(format_label, weekdays.iterrows()))
    return weekdays
def days_botN_view(month_indexes, N, weekday_df = weekdays_base):
    weekdays = (weekday_df[weekday_df['order_date'].dt.month
        .isin(month_indexes)]
        .groupby('order_date', as_index=False)
        .sum(True)
        .sort_values('quantity', ascending=True)
        .head(N)
    )
    weekdays["order_date"] = list(map(format_label, weekdays.iterrows()))
    return weekdays

def peak_hour_view(month_indexes, grouping = 1, hour_df = hour_base):
    peak_hour_data = hour_base.groupby('order_time', as_index=False).sum()
    total_days = len(df['order_date'].unique())
    peak_hour_data['quantity'] = peak_hour_data['quantity'].apply(lambda val : val/total_days)
    labels = peak_hour_data['order_time'].to_list()
    values = peak_hour_data['quantity'].to_list()
    bin2_labels = []
    bin2_values = []
    for i in range(0, 14, 2):
        bin2_labels.append(f"{labels[i]}~{labels[i+1]}")
        bin2_values.append(int(((values[i]+values[i+1])/2)*1000)/1000)
    return labels, values, bin2_labels, bin2_values

@st.cache_data
def flavors_base():
    flavors_sales = (df[['pizza_name', 'quantity',]]
        .groupby('pizza_name',as_index=False)
        .sum()
        .sort_values('quantity')
    )
    return flavors_sales

@st.cache_data
def flavors_ingredients_base():
    flavors_sales = (df[['pizza_name', 'pizza_ingredients', 'quantity',]]
        .groupby(['pizza_name', 'pizza_ingredients'],as_index=False)
        .sum()
        .sort_values('quantity')
    )
    return flavors_sales

flavors_df = flavors_base()
flavors_ingredients_df = flavors_ingredients_base()

def extract_ingredient_features(dataframe):
    res = dict()
    for i, row in dataframe.iterrows():
        for ingredient in row['pizza_ingredients'].split(", "):
            res[ingredient] = res.get(ingredient, 0) + 1
    feature_labels = []
    feature_values = []
    for tup in sorted(res.items(), key=lambda tup : tup[1]):
        feature_labels.append(tup[0])
        feature_values.append(tup[1])
    return feature_labels, feature_values

ingredients_list_full = extract_ingredient_features(flavors_ingredients_df)[0]

def flavors_view(N, _Ningr, ingredient_filter_list, flavors_base = flavors_ingredients_df):
    if len(ingredient_filter_list) > 0:
        pizza_sales = (flavors_base[
            ~flavors_base['pizza_ingredients'].str
                .contains("|".join(map(re.escape, ingredient_filter_list)))
            ]
        )
    else:
        pizza_sales = flavors_base

    topN = pizza_sales.tail(N)
    botN = pizza_sales.head(N)

    top_feature_labels, top_feature_values = extract_ingredient_features(pizza_sales)
    Ningr = min(_Ningr, len(top_feature_labels))
    return topN, botN, (top_feature_labels[-Ningr:], top_feature_values[-Ningr:]), (top_feature_labels[:Ningr], top_feature_values[:Ningr])



with st.sidebar:
    st.title("Configurações")
    st.slider("Escala de tamanho da pizza", 0.05, 1.5, 0.5, 0.01, format="%.2f", key="pizza_scale")
    st.checkbox("Slider para N-destaques?", key="day_slider")

with tab1:
    months = [
            "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho",
            "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]
    if "selected_months" not in st.session_state:
            st.session_state["selected_months"] = months
    st.multiselect("Meses", months, key="selected_months")

    with st.container():

        month_indexes = [
            months.index(m) + 1 for m in st.session_state["selected_months"]
        ]

        weekday_df = weekday_view(month_indexes)

        label_len = len(weekday_df.index)
        colors = sample_colorscale('Plasma', [i/(label_len-1) for i in range(label_len)])
        fig = go.Figure(
            data = [
                go.Bar(x=weekday_df.index, y=weekday_df['quantity'], marker_color=colors),
                go.Scatter(x=weekday_df.index,
                    y=[weekday_df['quantity'].mean()]*label_len,
                    mode="lines", line=dict(color="white", dash="dash"),
                    name=f"Média: {weekday_df['quantity'].mean()}"
                ),
            ],
            layout=dict(
                title="Movimento por dias da semana"
            )
        )
        col1, col2 = st.columns([2,1])
        with col1:
            st.plotly_chart(fig)
        with col2:
            st.image(pizza_scaled_plot(weekday_df.index, weekday_df['quantity']))
        
    st.divider()

    with st.container():
        if "N" not in st.session_state:
            st.session_state["N"] = 5

        top5_days_df = days_topN_view(month_indexes, st.session_state["N"])
        bot5_days_df = days_botN_view(month_indexes, st.session_state["N"])
        col1, col2, col3 = st.columns([5,1,5])
        
        label_len = len(top5_days_df.index)
        colors = sample_colorscale('Plasma', [i/(label_len-1) for i in range(label_len)])
        with col1:
            fig = go.Figure(
                data = [
                    go.Bar(x=top5_days_df['order_date'], y=top5_days_df['quantity'], marker_color=colors),
                ],
                layout=dict(
                    title=f"Top {st.session_state["N"]} dias mais movimentados"
                )
            )
            st.plotly_chart(fig)
        with col3:
            fig = go.Figure(
                data = [
                    go.Bar(x=bot5_days_df['order_date'], y=bot5_days_df['quantity'], marker_color=colors),
                ],
                layout=dict(
                    title=f"Bottom {st.session_state["N"]} dias mais movimentados"
                )
            )
            st.plotly_chart(fig)
        with col2:
            if st.session_state["day_slider"]:
                st.slider("Número de dias", 1, 100, step=1, key="N", value=st.session_state["N"])
            else:
                st.number_input("Número de dias", 1, 100, step=1, key="N", value=st.session_state["N"])

    st.divider()

    with st.container():
        peak_hour_tuples = peak_hour_view(month_indexes)

        label_len = len(peak_hour_tuples[0])
        colors = sample_colorscale('Plasma', [i/(label_len-1) for i in range(label_len)])
        fig = go.Figure(
            data = [
                go.Bar(x=peak_hour_tuples[0], y=peak_hour_tuples[1], marker_color=colors),
            ],
            layout=dict(
                title="Pedidos de pizza por horário"
            )
        )
        col1, col2 = st.columns([2,1])
        with col1:
            st.plotly_chart(fig)
        with col2:
            st.image(pizza_scaled_plot(peak_hour_tuples[2], peak_hour_tuples[3]))

with tab2:

    
    if "Npizzas" not in st.session_state:
            st.session_state["Npizzas"] = 5
    if "Nsabores" not in st.session_state:
            st.session_state["Nsabores"] = 10
    if "filtros_ingredientes" not in st.session_state:
            st.session_state["filtros_ingredientes"] = []

    col1,col2,col3 = st.columns([7,1,1])
    with col1:
        st.multiselect("Ingredientes filtrados", ingredients_list_full, key="filtros_ingredientes")

    if st.session_state["day_slider"]:
        with col2:
            st.slider("Número de sabores", 1, 100, step=1, key="Npizzas", value=st.session_state["Npizzas"])
        with col3:
            st.slider("Número de ingredientes", 1, 100, step=1, key="Nsabores", value=st.session_state["Nsabores"])
    else:
        with col2:
            st.number_input("Número de sabores", 1, 100, step=1, key="Npizzas", value=st.session_state["Npizzas"])
        with col3:
            st.number_input("Número de ingredientes", 1, 100, step=1, key="Nsabores", value=st.session_state["Nsabores"])

    
    topN, botN, top_features, bot_features = flavors_view(st.session_state["Npizzas"], st.session_state["Nsabores"], st.session_state["filtros_ingredientes"])

    col1, col2 = st.columns(2)
    with col1:
        label_len = len(topN.index)
        colors = sample_colorscale('Plasma', [i/(label_len-1) for i in range(label_len)])
        fig = go.Figure(
            data = [
                go.Bar(x=topN['pizza_name'], y=topN['quantity'], marker_color=colors),
            ],
            layout=dict(
                title=f"Top {st.session_state["Npizzas"]} sabores"
            )
        )
        st.plotly_chart(fig)
        fig = go.Figure(
            data = [
                go.Bar(x=botN['pizza_name'], y=botN['quantity'], marker_color=colors),
            ],
            layout=dict(
                title=f"Bot {st.session_state["Npizzas"]} sabores"
            )
        )
        st.plotly_chart(fig)

    with col2:
        label_len = len(top_features[0])
        colors = sample_colorscale('Plasma', [i/(label_len-1) for i in range(label_len)])
        fig = go.Figure(
            data = [
                go.Bar(y=top_features[0], x=top_features[1], marker_color=colors, orientation="h"),
            ],
            layout=dict(
                title=f"Top {st.session_state["Nsabores"]} ingredientes"
            )
        )
        st.plotly_chart(fig)
        fig = go.Figure(
            data = [
                go.Bar(y=bot_features[0], x=bot_features[1], marker_color=colors, orientation="h"),
            ],
            layout=dict(
                title=f"Bot {st.session_state["Nsabores"]} ingredientes"
            )
        )
        st.plotly_chart(fig)

with tab3:
    col1,col2 = st.columns(2)

    if "ingredientes_selecionados" not in st.session_state:
            st.session_state["ingredientes_selecionados"] = []
    if "k_sugestoes" not in st.session_state:
            st.session_state["k_sugestoes"] = 10

    with col1:
        bcol1, bcol2 = st.columns([5,1])
        with bcol1:
            st.multiselect("Ingredientes filtrados", ingredients_list_full, key="ingredientes_selecionados")
        with bcol2:
            if st.session_state["day_slider"]:
                st.slider("Número de sugestões", 1, 30, step=1, key="k_sugestoes", value=st.session_state["k_sugestoes"])
            else:
                st.number_input("Número de sugestões", 1, 30, step=1, key="k_sugestoes", value=st.session_state["k_sugestoes"])
        
        with st.container():
            display_text = modelo_cooc.top_k_sugestoes(st.session_state["k_sugestoes"], st.session_state["ingredientes_selecionados"])
            st.text("Ingredientes sugeridos:")
            if len(display_text)>0:
                st.markdown("- "+ "\n- ".join(display_text))

    with col2:
        texto = '''### Modelo de coocorrência

Para esse sistema de recomendação foi montado um modelo de coocorrências, algo como uma matriz de tamanho [Palavras, Ocorrencias de outras palavras].  
Para a contagem de ocorrências foram aplicados pesos: tanto para dar mais graça quanto para nivelar mais o que tornava o ingrediente de uma pizza sugerido que o outro.  
A fórmula para o valor de 'ocorrências' que acontecem são: $ \\frac{P}{QN} $, onde P é o preço total do subpedido, Q é a quantidade de pizzas do subpedido e N é o número de ingredientes na pizza (compensando para pizzas que tenham muitos ingredientes).
Diferentemente das semelhantes matrizes de co-ocorrência de PDI ou modelos de N-gramas em NLP, aqui a coocorrência leva em conta a pizza inteira (nem sequer poderia levar em conta só uma parte, pizzas não são sequenciais!).  
A amostragem é feita combinando as 'ocorrências' de cada ingrediente (token), normalizadas pelo seu número de ocorrências, e extraindo os top K ingredientes com maior valor.  
        '''
        with st.container():
            st.markdown(texto)
        