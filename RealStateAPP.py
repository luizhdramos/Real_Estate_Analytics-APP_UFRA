import geopandas
import streamlit as st
import pandas    as pd
import folium
from datetime import datetime
import mysql.connector as connection
from matplotlib import pyplot as plt
from matplotlib.ticker import StrMethodFormatter, NullFormatter
import plotly.express as px

from streamlit_folium import folium_static


st.set_page_config( layout='wide' )

st.image('UfraLogo.png', width=300)
st.title('Real Estate Analitycs App')

# ----(Carrehando Token Mapbox)----

token = open(r'MapboxToken.txt').read()

@st.cache( allow_output_mutation=True )
def get_data(Host, Database, User, Passwd, Query):
    try:
        mydb = connection.connect(host=Host, database=Database, user=User, passwd=Passwd, use_pure=True) #Conexão com o BD
        query = Query #Query da tabela house
        data = pd.read_sql(query,mydb) #Salvando resultado da Query em um pandas dataframe
        mydb.close() #fechando conexão com o BD
    except Exception as e:
        mydb.close()
        print(str(e))

    return data


@st.cache( allow_output_mutation=True )
def get_geofile( url ):
    geofile = geopandas.read_file( url )

    return geofile

#---------------------------------------------
#-----(Carregando dados do banco de dados)----
#---------------------------------------------
Host="localhost"
Database ='housedb'
User="root"
Passwd="Master2010"
Query="Select * from houses;"

data = get_data(Host, Database, User, Passwd, Query)



#---------------------------------------------
#-------------(Gerar geofile)-----------------
#---------------------------------------------

url = 'https://opendata.arcgis.com/datasets/83fc2e72903343aabff6de8cb445b81c_2.geojson'
geofile = get_geofile( url )



#---------------------------------------------
#------(Criando / Modificando Colunas )-------
#---------------------------------------------


#Editando tabela dates - para para datetime e no formato Ano, Mês e dia
data['dates'] = pd.to_datetime(data['dates']).dt.strftime('%Y-%m-%d')

#Criando tabela "year" em datetime e no formado Ano
data['year'] = pd.to_datetime( data['dates'] ).dt.strftime( '%Y' )

#Criando tabela "year_week" em datetime e no formado Ano-Mês
data['year_week'] = pd.to_datetime( data['dates'] ).dt.strftime( '%Y-%U' )

#Criando tabela "is_waterfront"
data['is_waterfront'] = data['waterfront'].apply( lambda x: 'sim' if x == 1 else 'não' )



#---------------------------------------------
#-----(Seleção de dados - menu lateral)-------
#---------------------------------------------

st.sidebar.title('Filtros')
# Codigo Postal
f_zipcode = st.sidebar.multiselect( 'Selecione o código postal', data['zipcode'].unique() )

#Filtro - Vista para o mar

f_isWaterfront = st.sidebar.checkbox('De frente para o mar')

# Preço
min_price = int( data['price'].min() )
max_price = int( data['price'].max() )
avg_price = int( data['price'].max() )
f_price = st.sidebar.slider( 'Preço máximo', min_price, max_price, avg_price, step=1 )

# Tamanho mínimo da sala de estar
min_living = int( data['sqft_living'].min() )
max_living = int( data['sqft_living'].max() )
avg_living = int( data['sqft_living'].min() )
f_living = st.sidebar.slider( 'Tamanho mínimo da sala de estar', min_living, max_living, avg_living, step=1 )

#Filtro - Numéro mínimo de banheiros
min_bathrooms = int( data['bathrooms'].min() )
max_bathrooms = int( data['bathrooms'].max() )
avg_bathrooms = int( data['bathrooms'].min() )
f_bathrooms = st.sidebar.slider( 'Numéro mínimo de banheiros', min_bathrooms, max_bathrooms, avg_bathrooms, step=1 )

#Filtro - Tamanho mínimo de sótão
min_basement = int( data['sqft_basement'].min() )
max_basement = int( data['sqft_basement'].max() )
avg_basement = int( data['sqft_basement'].min() )
f_basement = st.sidebar.slider( 'Tamanho mínimo de sótão', min_basement, max_basement, avg_basement, step=1 )

#Filtro - Condição Mínima
min_conditions = int( data['conditions'].min() )
max_conditions = int( data['conditions'].max() )
avg_conditions = int( data['conditions'].min() )
f_conditions = st.sidebar.slider( 'Condição Mínima', min_basement, max_basement, avg_basement, step=1 )


# setup filters
min_date = datetime.strptime( data['dates'].min(), '%Y-%m-%d' )
max_date = datetime.strptime( data['dates'].max(), '%Y-%m-%d' )
f_date = st.sidebar.slider( 'data', min_date, max_date, max_date )





#OK
if ( (f_zipcode != []) & (f_isWaterfront)):
    data = data.loc[data['zipcode'].isin( f_zipcode ) & (data['waterfront'] == 1)]
#OK
elif ( (f_zipcode != []) & (not f_isWaterfront) ):
    data = data.loc[data['zipcode'].isin( f_zipcode )]
#ok
elif ( (f_zipcode == []) & (f_isWaterfront)):
    data = data.loc[data['waterfront'] == 1]

else:
    data = data[(data['price'] < f_price) &
                (data['sqft_living'] > f_living) &
                (data['bathrooms'] > f_bathrooms) &
                (data['sqft_basement'] > f_basement) &
                (data['conditions'] > f_conditions) &
                (data['dates'] < f_date.strftime( '%Y-%m-%d' ))]
    




#----------------------------------------------
#---------(Carregando data frame)--------------
#----------------------------------------------

st.title( 'Dados' )
st.write( data.head(10) )


#----------------------------------------------
#----------(Mapa de Casas)----------------
#----------------------------------------------



st.title( 'Casas Disponíveis' )

fig = px.scatter_mapbox( data, 
                         lat="lat", 
                         lon="lon", 
                         color_discrete_sequence=['Gainsboro'],
                         size_max=15, 
                         height=300,
                         zoom=10)

fig.update_layout(mapbox_style='dark', mapbox_accesstoken=token)
fig.update_layout(height=600, margin={"r":0,"t":0,"l":0,"b":0})


st.plotly_chart(fig)




#----------------------------------------------
#----------(Densidade de Preço)----------------
#----------------------------------------------


st.title( 'Densidade de preço' )


df = data[['price', 'zipcode']].groupby( 'zipcode' ).mean().reset_index()
df.columns = ['ZIP', 'PRICE']

geofile = geofile[geofile['ZIP'].isin( df['ZIP'].tolist() )]

region_price_map = folium.Map( location=[data['lat'].mean(), 
                               data['lon'].mean() ],
                               default_zoom_start=15)
 
folium.TileLayer('cartodbdark_matter').add_to(region_price_map)

region_price_map.choropleth( data = df,
                             geo_data = geofile,
                             columns=['ZIP', 'PRICE'],
                             key_on='feature.properties.ZIP',
                             fill_color='YlOrRd',
                             fill_opacity = 0.7,
                             line_opacity = 0.2,
                             legend_name='AVG PRICE' )

folium_static( region_price_map )


#----------------------------------------------
#----------(Graficos de negócio)---------------
#----------------------------------------------

st.title( 'Gráficos de Negócios' )

fig1 = px.histogram( data, x='price', nbins=50)
fig2, ax2 = plt.subplots(figsize =(7, 5))
fig3, ax3 = plt.subplots(figsize =(7, 5))



#   ----(Histograma de distribuição de preço)----


#Criando Gráfico 1
st.title( 'Histograma de distribuição de preço' )
st.plotly_chart( fig1 )


#   ----(Gráfico 2 - Preço médio por semana)----

 #Criando Gráfico 2
st.title( "Preço médio por semana" )
data['year_week'] = pd.to_datetime( data['dates'] ).dt.strftime( '%Y-%U' )
by_week_of_year = data[['price', 'year_week']].groupby( 'year_week' ).mean().reset_index()
ax2.bar( by_week_of_year['year_week'], by_week_of_year['price'] )
ax2.tick_params(axis='x', rotation=60)

# Retira notação científica -  Gráfico 2
ax2.yaxis.set_major_formatter(StrMethodFormatter('{x:.0f}'))
ax2.yaxis.set_minor_formatter(NullFormatter())

st.plotly_chart(fig2, use_container_width=True)

#   ----(Gráfico 3 - Preço médio por dia)----
st.title( "Preço médio por dia" )
# Criando Gráfico 3 - Preço médio por dia
by_day = data[['price', 'dates']].groupby( 'dates' ).mean().reset_index()
ax3.plot( by_day['dates'], by_day['price'] )
ax3.tick_params(axis='x', rotation=60)

# Retira notação científica - Gráfico 3
ax3.yaxis.set_major_formatter(StrMethodFormatter('{x:.0f}'))
ax3.yaxis.set_minor_formatter(NullFormatter())

st.plotly_chart(fig3, use_container_width=True)


