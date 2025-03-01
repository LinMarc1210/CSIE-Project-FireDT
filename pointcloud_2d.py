import pyrealsense2 as rs
import numpy as np
import pandas as pd
import cv2
import time

# 初始化 RealSense 設備
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
pipeline.start(config)

try:
    while True:
        frames = pipeline.wait_for_frames()

        # **確保深度影像與 RGB 影像同步**
        align = rs.align(rs.stream.color)
        aligned_frames = align.process(frames)
        depth_frame = aligned_frames.get_depth_frame()
        color_frame = aligned_frames.get_color_frame()

        if not depth_frame or not color_frame:
            continueframes = pipeline.wait_for_frames()

        # 讀取 BGR 影像
        color_image = np.asanyarray(color_frame.get_data())

        # **計算點雲**
        pc = rs.pointcloud()
        pc.map_to(color_frame)  # **確保點雲對應到 color_frame**
        points = pc.calculate(depth_frame)  # 取得點雲
        

        # 讀取點雲 XYZ 座標
        vtx = np.asanyarray(points.get_vertices()).view(np.float32).reshape(-1, 3)

        # 讀取點雲的 UV 紋理座標
        tex = np.asanyarray(points.get_texture_coordinates()).view(np.float32).reshape(-1, 2)

        # 過濾無效點 (Z <= 0)
        valid_mask = vtx[:, 2] > 0
        vtx = vtx[valid_mask]
        tex = tex[valid_mask]

        # **修正 UV 轉換**
        img_h, img_w = color_image.shape[:2]
        tex_x = np.clip((tex[:, 0] * (img_w - 1)).astype(int), 0, img_w - 1)
        tex_y = np.clip((tex[:, 1] * (img_h - 1)).astype(int), 0, img_h - 1)

        # 取得點對應的顏色
        colors = color_image[tex_y, tex_x]  # **從 color_image 擷取對應顏色**

        # **建立一張全黑的影像來顯示 3D 點雲投影**
        blank_image = np.zeros((img_h, img_w, 3), dtype=np.uint8)

        # **在全黑背景上畫出投射完的點雲**
        for i in range(len(tex_x)):
            r, g, b = colors[i]
            cv2.circle(blank_image, (tex_x[i], tex_y[i]), 2, (int(r), int(g), int(b)), -1)

        # **合併影像**
        combined_image = np.hstack((color_image, blank_image))

        # **顯示影像**
        cv2.imshow('RealSense - Left: RGB | Right: 3D Projection', combined_image)

        # **按鍵處理**
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break  # 按下 'q' 離開
        elif key == ord('s'):
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            cv2.imwrite(f"color_{timestamp}.png", color_image)
            cv2.imwrite(f"projection_{timestamp}.png", blank_image)
            print(f"[INFO] saved color_{timestamp}.png and projection_{timestamp}.png")
            data = {
                'x': vtx[:, 0],
                'y': vtx[:, 1],
                'z': vtx[:, 2],
                'u': tex_x,
                'v': tex_y,
                'R': colors[:, 2],  # OpenCV 使用 BGR 格式，R 在第 2 列
                'G': colors[:, 1],
                'B': colors[:, 0]
            }
            df = pd.DataFrame(data)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            df.to_csv(f"pointcloud_{timestamp}.csv", index=False)
            print(f"[INFO] saved pointcloud_{timestamp}.csv")

finally:
    pipeline.stop()
    cv2.destroyAllWindows()
