import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import json
import calendar
import streamlit as st
from sqlalchemy import create_engine
import seaborn as sns
import re

# Função para carregar dados
def load_data():
    # String de conexão ao banco de dados com Trusted Connection
    connection_string = 'mssql+pyodbc://@apml_tes/Sandbox?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'

    # Criar engine de conexão
    engine = create_engine(connection_string)

    # Consultar dados da tabela 'AnaliseJustificativaFalta'
#     query = """
# select * from AnaliseJustificativaFalta nolock
# union all
# select * from [AnaliseJustificativaFalta2024] nolock"""
#     df = pd.read_sql(query, engine)
    df = pd.read_csv('amostra_AnaliseJustificativaFalta.csv')
    return df

# Função para converter as listas de strings em listas reais e achatar
def flatten_reason_lists(column_data):
    reasons = []
    for item in column_data.dropna():
        try:
            reason_list = re.findall(r"'(.*?)'", item)
            reasons.extend(reason_list)
        except (ValueError, SyntaxError):
            continue
    return reasons

# Função para gerar nuvem de palavras com stopwords adicionais
def generate_word_cloud_with_stopwords(data, title, stopwords):
    if len(data) == 0:
        st.write(f"Sem dados suficientes para gerar a nuvem de palavras: {title}")
        return
    text = ' '.join(data)
    wordcloud = WordCloud(width=800, height=400, background_color='white', stopwords=stopwords).generate(text)
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.title(title)
    st.pyplot(plt.gcf())
    plt.clf()  # Limpar a figura após renderizar

# Função para categorizar os níveis de subjetividade
def categorizar_subjetividade(valor):
    if valor < 0.3:
        return 'Baixo'
    elif valor < 0.6:
        return 'Médio'
    else:
        return 'Alto'

# Função para gerar todas as visualizações para um mês especificado
def generate_monthly_visualizations(df, year, month):
    df_filtered = df[(df['AnoAtividade'] == year) & (df['MesAtividade'] == month)]
    
    if df_filtered.empty:
        st.write(f"Sem dados para {calendar.month_name[month]} {year}.")
        return

    perfil_comportamental = df_filtered['Perfil_Comportamental'].dropna()
    sentimentos = df_filtered['Sentimentos'].dropna()
    contribuicoes = df_filtered['Contribuicoes'].dropna()
    palavras_chave = df_filtered['Palavras_Chave'].dropna()
    motivo_justificativa = df_filtered['Razoes_Possiveis']
    flattened_reasons = flatten_reason_lists(motivo_justificativa)

    def safe_extract_keys(val):
        try:
            return re.findall(r"'(.*?)'", val)
        except Exception as e:
            return []

    contribuicoes_negativas = df_filtered['Contribuicoes'].apply(lambda x: safe_extract_keys(x) if isinstance(x, str) else {})
    all_frases_contribuicoes_negativas_cleaned = ' '.join([k for contrib in contribuicoes_negativas for k in contrib if isinstance(k, str)])
        
    # Gerar nuvens de palavras
    additional_stopwords = set(['não', 'a', 'o', 'e', 'de', 'para', 'com', 'do', 'da', 'em', 'um', 'uma', 'que', 'se', 'os', 'as'])
    generate_word_cloud_with_stopwords(all_frases_contribuicoes_negativas_cleaned.split(), 'Frases Negativas - Contribuições', additional_stopwords)

    generate_word_cloud_with_stopwords(flattened_reasons, f'Nuvem de Palavras dos Motivos das Justificativas - {calendar.month_name[month]} {year}', additional_stopwords)
    generate_word_cloud_with_stopwords(perfil_comportamental, f'Nuvem de Palavras de Perfil Comportamental - {calendar.month_name[month]} {year}', additional_stopwords)
    generate_word_cloud_with_stopwords(sentimentos, f'Nuvem de Palavras de Sentimentos - {calendar.month_name[month]} {year}', additional_stopwords)
    generate_word_cloud_with_stopwords(palavras_chave, f'Nuvem de Palavras das Palavras-Chave - {calendar.month_name[month]} {year}', additional_stopwords)

    # Gráfico de barras para NomeAtividade
    nome_atividade_counts = df_filtered['NomeAtividade'].value_counts()
    plt.figure(figsize=(12, 6))
    nome_atividade_counts.plot(kind='bar')
    plt.title(f'Contagem de NomeAtividade - {calendar.month_name[month]} {year}')
    plt.xlabel('NomeAtividade')
    plt.ylabel('Contagem')
    st.pyplot(plt.gcf())
    plt.clf()  # Limpar a figura após renderizar

    # Gráficos de pizza para falha_sistemica e falha_operacional
    falha_sistemica_counts = df_filtered['falha_sistemica'].value_counts()
    falha_operacional_counts = df_filtered['falha_operacional'].value_counts()

    plt.figure(figsize=(14, 7))
    plt.subplot(1, 2, 1)
    falha_sistemica_counts.plot(kind='pie', autopct='%1.1f%%', startangle=140, colors=['#ff9999','#66b3ff'])
    plt.title(f'Distribuição de Falhas Sistêmicas - {calendar.month_name[month]} {year}')
    plt.subplot(1, 2, 2)
    falha_operacional_counts.plot(kind='pie', autopct='%1.1f%%', startangle=140, colors=['#ff9999','#66b3ff'])
    plt.title(f'Distribuição de Falhas Operacionais - {calendar.month_name[month]} {year}')
    plt.tight_layout()
    st.pyplot(plt.gcf())
    plt.clf()  # Limpar a figura após renderizar

    # Analisar a distribuição do nível de subjetividade e sua relação com a aceitação das justificativas
    df_filtered['Nivel_Subjetividade_Categoria'] = df_filtered['Nivel_Subjetividade'].apply(categorizar_subjetividade)
    plt.figure(figsize=(12, 6))
    sns.countplot(x='Nivel_Subjetividade_Categoria', data=df_filtered)
    plt.title('Distribuição dos Níveis de Subjetividade')
    plt.xlabel('Nível de Subjetividade')
    plt.ylabel('Contagem')
    st.pyplot(plt.gcf())
    plt.clf()  # Limpar a figura após renderizar

    plt.figure(figsize=(12, 6))
    sns.countplot(x='Nivel_Subjetividade_Categoria', hue='DescricaoSituacao', data=df_filtered)
    plt.title('Relação entre Nível de Subjetividade e Aceitação das Justificativas')
    plt.xlabel('Nível de Subjetividade')
    plt.ylabel('Contagem')
    plt.legend(title='Situação')
    st.pyplot(plt.gcf())
    plt.clf()  # Limpar a figura após renderizar


# Configuração do Streamlit
st.title('Dashboard de Justificativas de Faltas')
st.sidebar.title('Filtros')

# Carregar os dados
df = load_data()

# Adicionando seletores de ano e mês
anos = df['AnoAtividade'].unique()
ano_selecionado = st.sidebar.selectbox('Selecione o Ano', anos)

meses = sorted(df['MesAtividade'].unique())
mes_selecionado = st.sidebar.selectbox('Selecione o Mês', meses)

# Botão para gerar visualizações
if st.sidebar.button('Gerar Visualizações'):
    generate_monthly_visualizations(df, ano_selecionado, mes_selecionado)
