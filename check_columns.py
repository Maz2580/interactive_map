import geopandas as gpd

SHAPEFILE_PATH = "data/Data_for_interactiveMap/Path_conectivity_data_all_years.shp"

try:
    gdf = gpd.read_file(SHAPEFILE_PATH)
    print("Shapefile loaded successfully.")
    print("Columns:", gdf.columns)
except Exception as e:
    print(f"Error loading or reading shapefile: {e}")
