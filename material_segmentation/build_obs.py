import numpy as np
import json
import pandas as pd
import os

# 定義實際空間大小（單位：米）
# x,y,z 方向：右、下、前
def get_cluster_bounds(cluster_points):
    """根據聚類點計算邊界"""
    if len(cluster_points) == 0:
        return None
    x_min, x_max = np.min(cluster_points['x']), np.max(cluster_points['x'])
    y_min, y_max = np.min(cluster_points['y']), np.max(cluster_points['y'])
    z_min, z_max = np.min(cluster_points['z']), np.max(cluster_points['z'])
    
    return {
        "x_min": float(x_min),
        "x_max": float(x_max),
        "y_min": float(y_min),
        "y_max": float(y_max),
        "z_min": float(z_min),
        "z_max": float(z_max)
    }

def build_obs_json(input_path: str, SPACE_X: float = 10.0, SPACE_Y: float = 3.0, SPACE_Z: float = 8.0) -> dict:
    df = pd.read_csv(input_path)
    
    # 計算縮放比例
    x_scale = SPACE_X / (df['x'].max() - df['x'].min())
    y_scale = SPACE_Y / (df['y'].max() - df['y'].min())
    z_scale = SPACE_Z / (df['z'].max() - df['z'].min())
    df['x'] = (df['x'] - df['x'].min()) * x_scale
    df['y'] = (df['y'] - df['y'].min()) * y_scale
    df['z'] = (df['z'] - df['z'].min()) * z_scale
    
    output_data = {
        "space_dimensions": {
            "x": float(SPACE_X),
            "y": float(SPACE_Y),
            "z": float(SPACE_Z)
        },
        "objects": []
    }
    
    unique_clusters = df['cluster'].unique()
    for cluster_id in unique_clusters:
        if cluster_id == -1:
            continue

        cluster_points = df[df['cluster'] == cluster_id]
        
        if len(cluster_points) == 0:
            continue
            
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "categories.txt"), "r") as f:
            categories = [line.strip() for line in f.readlines()]
        main_material = cluster_points['material'].mode().iloc[0]
        main_material_id = categories.index(main_material)


        bounds = get_cluster_bounds(cluster_points)
        if bounds is None:
            continue
        
        output_data["objects"].append({
            "cluster_id": int(cluster_id),
            "object_label": cluster_points['object_label'].iloc[0],
            "material": {
                "id": int(main_material_id),
                "name": categories[int(main_material_id)]
            },
            "bounds": bounds,
            "dimensions": {
                "depth": float(bounds["x_max"] - bounds["x_min"]),
                "width": float(bounds["y_max"] - bounds["y_min"]),
                "height": float(bounds["z_max"] - bounds["z_min"])
            }
        })
    
    output_path = os.path.join(os.path.dirname(os.path.dirname(input_path)), "room_simulation.json")
    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=4)
        
    return {
        'output_json': output_path,
    }

# only for testing
if __name__ == "__main__":
    input_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results', 'clustered_points.csv')
    build_obs_json(input_path)
