import folium
from folium.plugins import Fullscreen
import streamlit as st
from streamlit_folium import st_folium
from st_btn_select import st_btn_select

import geopandas as gpd
from shapely.geometry import Point
import networkx as nx
import osmnx as ox

def main():

  st.set_page_config(layout='wide')

  st.header("The 15 minute city 🌳", divider='rainbow')
  st.subheader('Select a city and a transportation mode to see how far you could go in 15 minutes from a selected point on the map.')

  # center on The Netherlands
  CENTER_START = [52.1326, 5.2913]
  ZOOM_START = 8
  # city coordinates and zoom levels
  eindhoven_ltlon = [51.4398, 5.4785]
  eindhoven_zoom = 12
  leiden_ltlon = [52.1584, 4.4937]
  leiden_zoom = 12
  haarlem_ltlon = [52.3874, 4.6462]
  haarlem_zoom = 12

  if 'city' not in st.session_state:
      st.session_state['city'] = 'Eindhoven, The Netherlands'
  if 'center' not in st.session_state:
      st.session_state['center'] = [52.1326, 5.2913]
  if 'zoom' not in st.session_state:
      st.session_state['zoom'] = 12
  if 'isochrones' not in st.session_state:
      st.session_state['isochrones'] = []
  if 'transport' not in st.session_state:
      st.session_state['transport'] = 'walk'
  if 'speed' not in st.session_state:
      st.session_state['speed'] = 4.5
  if 'time' not in st.session_state:
      st.session_state['time'] = 15
  if "last_clicked" not in st.session_state:
        st.session_state["last_clicked"] = None

  col1, col2 = st.columns(2)
  col1.write('Select a city:')
  with col1:
      city = st_btn_select(('eindhoven', 'leiden', 'haarlem'),
    format_func=lambda name: name.capitalize(),)

  if city == 'eindhoven':
     st.session_state['city'] = 'Eindhoven, The Netherlands'
     st.session_state['center'] = eindhoven_ltlon
     st.session_state['zoom'] = eindhoven_zoom
  elif city == 'leiden':
      st.session_state['city'] = 'Leiden, The Netherlands'
      st.session_state['center'] = leiden_ltlon
      st.session_state['zoom'] = leiden_zoom
  elif city == 'haarlem':
      st.session_state['city'] = 'Haarlem, The Netherlands'
      st.session_state['center'] = haarlem_ltlon
      st.session_state['zoom'] = haarlem_zoom

  col2.write('Select a transportation mode:')
  with col2:
      transport = st_btn_select(('walk 🚶‍♀️', 'bike 🚴‍♀️', 'drive 🚗'),
    format_func=lambda name: name.capitalize(),)
  
  if transport == 'walk 🚶‍♀️':
      st.session_state['transport'] = 'walk'
      st.session_state['speed'] = 4.5
  elif transport == 'bike 🚴‍♀️':
      st.session_state['transport'] = 'bike'
      st.session_state['speed'] = 15
  elif transport == 'drive 🚗':
      st.session_state['transport'] = 'drive'
      st.session_state['speed'] = 50

  @st.cache_data
  def get_nodes(city, transport):
      graph = ox.graph_from_place(st.session_state['city'], network_type=st.session_state['transport'], simplify=True)
      # gdf_nodes = ox.graph_to_gdfs(graph, edges=False)
      return graph
  
  G = get_nodes(st.session_state['city'], st.session_state['transport'])

  m = folium.Map(location=CENTER_START, zoom_start=ZOOM_START)
  Fullscreen().add_to(m)
  fg = folium.FeatureGroup(name='Isochrone')
  for isochrone in st.session_state['isochrones']:
      fg.add_child(isochrone)

  map = st_folium(
      m,
      center=st.session_state['center'],
      zoom=st.session_state['zoom'],
      feature_group_to_add=fg,
      height=700,
      width='100%'
  )
  
  def get_nearest_node(lat, lon, graph):
      nearest_node = ox.distance.nearest_nodes(graph, lat, lon)
      graph = ox.project_graph(graph)
      return nearest_node
      

  if (map['last_clicked'] and map['last_clicked'] != st.session_state['last_clicked']):
    st.session_state['last_clicked'] = map['last_clicked']
    nearest_node = get_nearest_node(map['last_clicked']['lng'], map['last_clicked']['lat'], G)

    # add an edge attribute for time in minutes required to traverse each edge
    meters_per_minute = st.session_state['speed'] * 1000 / 60  # km per hour to m per minute
    for _, _, _, data in G.edges(data=True, keys=True):
        data["time"] = data["length"] / meters_per_minute

    isochrone_polys = []
    subgraph = nx.ego_graph(G, nearest_node, radius=st.session_state['time'], distance="time")
    node_points = [Point((data["x"], data["y"])) for node, data in subgraph.nodes(data=True)]
    bounding_poly = gpd.GeoSeries(node_points).unary_union.convex_hull
    isochrone_polys.append(bounding_poly)
    gdf = gpd.GeoDataFrame(geometry=isochrone_polys)
    geo_j = gpd.GeoSeries(gdf["geometry"]).to_json()
    geo_j = folium.GeoJson(data=geo_j, style_function=lambda x: {"fillColor": "orange"})
    st.session_state['isochrones'] = [geo_j]
    st.experimental_rerun()

if __name__ == '__main__':
  main()