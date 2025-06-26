import geopandas as gpd
import folium
from folium.plugins import HeatMap, FeatureGroupSubGroup, MarkerCluster
import branca.colormap as cm

# --- Configuration ---
SHAPEFILE_PATH = "data/Data_for_interactiveMap/Path_conectivity_data_all_years.shp"
OUTPUT_HTML_PATH = "interactive_map.html" # Will save in the root for now
DELIV_YEAR_COL = 'Deliv_Year'
CATEGORY_COL = 'category'
LOCATION_COL = 'location' # For tooltips

# Categories for heatmaps (as requested by user)
HEATMAP_CATEGORIES = [1, 2]

# --- Helper Functions ---
def get_representative_points(geometry):
    """
    Extracts points from geometries. For LineStrings, uses all vertices.
    For Polygons, uses the centroid. For Points, uses the point itself.
    Returns a list of (latitude, longitude) tuples.
    """
    points = []
    if geometry.geom_type == 'LineString':
        for point in geometry.coords: # Corrected: geometry.coords directly gives tuples
            points.append((point[1], point[0])) # Folium uses (lat, lon)
    elif geometry.geom_type == 'Polygon':
        centroid = geometry.centroid
        points.append((centroid.y, centroid.x))
    elif geometry.geom_type == 'Point':
        points.append((geometry.y, geometry.x))
    return points

def get_all_points_from_gdf(gdf):
    """Extracts all representative points from a GeoDataFrame."""
    all_coords = []
    for geom in gdf.geometry:
        all_coords.extend(get_representative_points(geom))
    return all_coords

# --- Main Script ---
def generate_map():
    print(f"Loading shapefile from: {SHAPEFILE_PATH}")
    try:
        gdf = gpd.read_file(SHAPEFILE_PATH)
    except Exception as e:
        print(f"Error loading shapefile: {e}")
        return

    print(f"Shapefile loaded. CRS: {gdf.crs}")
    if gdf.crs != "EPSG:4326":
        print(f"Reprojecting to EPSG:4326...")
        gdf = gdf.to_crs("EPSG:4326")
        print(f"Reprojection complete. New CRS: {gdf.crs}")

    if gdf.empty:
        print("GeoDataFrame is empty after loading.")
        return

    # Calculate map center
    try:
        # Use unary_union to get a single geometry representing all features, then get its centroid
        map_center_geom = gdf.unary_union.centroid
        map_center = [map_center_geom.y, map_center_geom.x]
    except Exception as e:
        print(f"Could not calculate centroid from unary_union ({e}), falling back to first geometry's centroid.")
        if not gdf.geometry.empty and gdf.geometry.iloc[0] is not None:
            map_center = [gdf.geometry.iloc[0].centroid.y, gdf.geometry.iloc[0].centroid.x]
        else:
            print("No valid geometries to determine center. Defaulting to (0,0).")
            map_center = [0,0] # Default if no geometries

    print(f"Calculated map center: {map_center}")
    m = folium.Map(location=map_center, zoom_start=10, tiles="CartoDB positron")

    # --- 1. Heatmaps for Categories ---
    print("\nGenerating heatmaps...")
    for cat_val in HEATMAP_CATEGORIES:
        cat_gdf = gdf[gdf[CATEGORY_COL] == cat_val]
        if not cat_gdf.empty:
            print(f"Processing Category {cat_val} for heatmap ({len(cat_gdf)} features)...")
            heat_data = get_all_points_from_gdf(cat_gdf)
            if heat_data:
                HeatMap(heat_data, name=f"Heatmap - Category {cat_val}").add_to(m)
                print(f"Added Heatmap for Category {cat_val} with {len(heat_data)} points.")
            else:
                print(f"No points found for Category {cat_val} heatmap.")
        else:
            print(f"No data found for Category {cat_val}.")

    # --- 2. Data Layers per Deliv_Year ---
    print("\nGenerating layers per Deliv_Year...")
    unique_years = sorted(gdf[DELIV_YEAR_COL].unique().tolist())
    print(f"Unique Delivery Years: {unique_years}")

    # Create a parent FeatureGroup for all yearly data to manage them better
    yearly_data_group = folium.FeatureGroup(name="Yearly Connectivity Data", show=False).add_to(m) # Start with this group hidden

    # Colormap for different years (optional, but can make lines distinct if not using markers)
    # colors = ['blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue', 'pink', 'lightblue', 'lightgreen', 'gray', 'black', 'lightgray']
    # year_color_map = {year: colors[i % len(colors)] for i, year in enumerate(unique_years)}

    for year in unique_years:
        year_gdf = gdf[gdf[DELIV_YEAR_COL] == year]
        if not year_gdf.empty:
            print(f"Processing {DELIV_YEAR_COL} {year} ({len(year_gdf)} features)...")

            # Create a FeatureGroup for each year, nested under the main yearly_data_group
            # This allows finer control with FeatureGroupSubGroup if needed, or just better organization
            year_fg_name = f"Year: {year}"
            year_fg = folium.FeatureGroup(name=year_fg_name, show=False) # Each year layer also starts hidden

            # Option 1: Add GeoJSON directly (good for lines/polygons)
            folium.GeoJson(
                year_gdf.__geo_interface__, # Convert GeoDataFrame to GeoJSON dict
                name=f"Data for {year}",
                style_function=lambda x: {'color': 'blue', 'weight': 2, 'opacity': 0.7}, # Simple style
                tooltip=folium.GeoJsonTooltip(fields=[LOCATION_COL, CATEGORY_COL, DELIV_YEAR_COL], aliases=['Location:', 'Category:', 'Year:'])
            ).add_to(year_fg)
            
            # Option 2: Add markers at centroids (if points are preferred for some reason, or for popups)
            # Note: For LineStrings, this would be centroids of lines.
            # marker_cluster_year = MarkerCluster(name=f"Markers {year}").add_to(year_fg)
            # for idx, row in year_gdf.iterrows():
            #     geom = row.geometry
            #     if geom:
            #         centroid = geom.centroid
            #         popup_html = f"<b>Year:</b> {row[DELIV_YEAR_COL]}<br>" \
            #                      f"<b>Category:</b> {row[CATEGORY_COL]}<br>" \
            #                      f"<b>Location:</b> {row.get(LOCATION_COL, 'N/A')}"
            #         folium.Marker(
            #             location=[centroid.y, centroid.x],
            #             popup=folium.Popup(popup_html, max_width=300),
            #             tooltip=f"{row.get(LOCATION_COL, 'Feature')} ({row[DELIV_YEAR_COL]})"
            #         ).add_to(marker_cluster_year)

            year_fg.add_to(yearly_data_group) # Add the year's FeatureGroup to the parent group
            print(f"Added GeoJSON layer for {year}.")
        else:
            print(f"No data found for {DELIV_YEAR_COL} {year}.")

    # --- Add Layer Control ---
    print("\nAdding Layer Control...")
    folium.LayerControl(collapsed=False).add_to(m)

    # --- Save Map ---
    try:
        m.save(OUTPUT_HTML_PATH)
        print(f"\nInteractive map saved to: {OUTPUT_HTML_PATH}")
    except Exception as e:
        print(f"Error saving map: {e}")

if __name__ == "__main__":
    generate_map()
