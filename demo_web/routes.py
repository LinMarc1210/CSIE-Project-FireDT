from flask import (
    render_template, request, redirect, url_for,
    send_file, abort, flash, session, jsonify
)
from datetime import datetime
from demo_web import app, db
from demo_web.models import User, File
from demo_web.utils import save_uploaded_files
from demo_web.pipeline import run_pipeline
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import logging
import os 
import subprocess

VIDEO_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'material_segmentation', 'fds_output')
AVI_PATH = os.path.join(VIDEO_DIR, "movie_fire.avi")
AVI_PATH_2 = os.path.join(VIDEO_DIR, "movie_smoke.avi")

NEW_VIDEO_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'material_segmentation', 'videos')


# @app.route('/')
# def index():
#     return render_template('index.html', video_url=None)

# # 用來標記是否正在上傳
# @app.before_request
# def check_upload_status():
#     # 阻止同一使用者在進行上傳過程中的重複上傳
#     if session.get(f'uploading_{current_user.id}', False):
#         return jsonify({'error': 'You are already uploading a file, please wait until the current upload is finished.'})

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', video_url=None)

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    # 2. 查詢資料庫，看有沒有這個 username
    user = User.query.filter_by(username=username).first()

    # 3. 如果找不到 user，或是密碼比對失敗
    if user is None or not user.check_password(password):
        flash('帳號或密碼錯誤，請重新嘗試。', 'danger')
        return redirect('/login')

    # 4. 代表帳號存在且密碼正確，呼叫 login_user 將使用者登入
    login_user(user, remember=True)  # Set current_user as authenticated

    # Debug: Check if user is authenticated
    print(f"Is user authenticated? {current_user.is_authenticated}")

    return render_template('member.html', user=user)


@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username', '').strip()
    email    = request.form.get('email', '').strip()
    password = request.form.get('password', '')

    
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return redirect(url_for('error', msg='user already exists'))

    existing_email = User.query.filter_by(email=email).first()
    if existing_email:
        return redirect(url_for('error', msg='email is already registered'))
    
    # new user
    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    return redirect('/')
    

@app.route('/login', methods=['GET'])
def show_login():
    return render_template('login.html')

@app.route('/register', methods=['GET'])
def show_register():
    return render_template('register.html')

@app.route('/api/upload', methods=['POST'])
def upload_files():
    if 'files' not in request.files:
        return redirect(url_for('index'))

    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return redirect(url_for('index'))

    saved_files, error_msg = save_uploaded_files(files)
    if saved_files is None:
        return redirect(url_for('error_page', msg=error_msg))

    try:
        data_path = saved_files[0]
        # data_path = os.path.join(os.path.dirname(__file__), '20250605_171517.bag')
        result = run_pipeline(pic_input=data_path)

        # 生成檔案名稱，包含使用者ID與上傳時間
        current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        logging.debug(f"Is user authenticated? {current_user.is_authenticated}")
        
        if current_user.is_authenticated:
            # ✅ 修正：使用一致的命名格式
            filename_fire = f"{current_user.id}_fire_{current_time}.mp4"
            filename_smoke = f"{current_user.id}_smoke_{current_time}.mp4"  # ✅ 修正：smoke而不是fire
        else:
            filename_fire = f"anonymous_fire_{current_time}.mp4"  # ✅ 匿名用户也加时间戳避免冲突
            filename_smoke = f"anonymous_smoke_{current_time}.mp4"

        # 使用靜態路徑來儲存影片
        MP4_PATH_DYNAMIC = os.path.join(NEW_VIDEO_DIR, filename_fire)
        MP4_PATH_2_DYNAMIC = os.path.join(NEW_VIDEO_DIR, filename_smoke)

        # 處理第一個影片
        if os.path.exists(AVI_PATH):
            if os.path.exists(MP4_PATH_DYNAMIC):
                try:
                    os.remove(MP4_PATH_DYNAMIC)
                except OSError:
                    pass
            subprocess.run([
                "ffmpeg",
                "-y",
                "-i", AVI_PATH,
                "-c:v", "libx264",
                "-c:a", "aac",
                MP4_PATH_DYNAMIC
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # 儲存影片資料到資料庫
            if current_user.is_authenticated:
                video1 = File(user_id=current_user.id, file_name=filename_fire, file_path=MP4_PATH_DYNAMIC)
                db.session.add(video1)
        else:
            return redirect(url_for('error_page', msg=f"找不到影片檔：{AVI_PATH}"))

        # 處理第二個影片
        if os.path.exists(AVI_PATH_2):
            if os.path.exists(MP4_PATH_2_DYNAMIC):
                try:
                    os.remove(MP4_PATH_2_DYNAMIC)
                except OSError:
                    pass
            subprocess.run([
                "ffmpeg",
                "-y",
                "-i", AVI_PATH_2,
                "-c:v", "libx264",
                "-c:a", "aac",
                MP4_PATH_2_DYNAMIC
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # 儲存第二個影片資料到資料庫
            if current_user.is_authenticated:
                video2 = File(user_id=current_user.id, file_name=filename_smoke, file_path=MP4_PATH_2_DYNAMIC)
                db.session.add(video2)
        else:
            return redirect(url_for('error_page', msg=f"找不到第二個影片檔：{AVI_PATH_2}"))

        # 提交資料到資料庫
        if current_user.is_authenticated:
            db.session.commit()
            # ✅ 将文件名信息传递给下一个路由
            return redirect(url_for('member', fire_file=filename_fire, smoke_file=filename_smoke))
        else:
            return redirect(url_for('video', fire_file=filename_fire, smoke_file=filename_smoke))

    except subprocess.CalledProcessError as e:
        return redirect(url_for('error_page', msg=f"轉檔失敗: {e}"))
    except Exception as e:
        return redirect(url_for('error_page', msg=f'Pipeline 或轉檔執行失敗: {e}'))


@app.route('/video')
def video():
    # 获取传递的文件名
    fire_file = request.args.get('fire_file')
    smoke_file = request.args.get('smoke_file')
    
    if not fire_file or not smoke_file:
        return abort(404, "缺少视频文件信息")
    
    # 检查文件是否存在
    video_path_1 = os.path.join(NEW_VIDEO_DIR, fire_file)
    video_path_2 = os.path.join(NEW_VIDEO_DIR, smoke_file)
    
    if not os.path.exists(video_path_1) or not os.path.exists(video_path_2):
        return abort(404, "视频文件不存在")

    # 传递视频 URL
    video_urls = {
        "video1": url_for('send_video_by_name', filename=fire_file),
        "video2": url_for('send_video_by_name', filename=smoke_file)
    }
    
    return render_template('index.html', video_urls=video_urls)
# ✅ 新增：通过文件名发送视频的路由
@app.route('/send_video_by_name/<filename>')
def send_video_by_name(filename):
    # 安全检查：确保文件名只包含允许的字符
    import re
    if not re.match(r'^[a-zA-Z0-9_\-\.]+$', filename):
        return abort(404)
    
    video_path = os.path.join(NEW_VIDEO_DIR, filename)
    
    if not os.path.exists(video_path):
        return abort(404)
    
    return send_file(video_path, mimetype='video/mp4')

# 設定基本的 logging 配置
logging.basicConfig(level=logging.DEBUG)

@app.route('/member')
@login_required
def member():
    user_id = current_user.id
    logging.debug(f"User ID: {user_id}")

    # 查询该使用者的历史纪录
    files = File.query.filter_by(user_id=user_id).all()
    
    if files:
        logging.debug(f"Found {len(files)} files for user ID {user_id}")
    else:
        logging.debug(f"No files found for user ID {user_id}")

    # ✅ 检查是否有刚上传的视频需要显示
    video_urls = None
    fire_file = request.args.get('fire_file')
    smoke_file = request.args.get('smoke_file')
    
    if fire_file and smoke_file:
        # 使用传递的文件名
        video_path_1 = os.path.join(NEW_VIDEO_DIR, fire_file)
        video_path_2 = os.path.join(NEW_VIDEO_DIR, smoke_file)
        
        if os.path.exists(video_path_1) and os.path.exists(video_path_2):
            video_urls = {
                "video1": url_for('send_video_by_name', filename=fire_file),
                "video2": url_for('send_video_by_name', filename=smoke_file)
            }
    else:
        # ✅ 如果没有传递文件名，查找最新的视频文件
        import glob
        fire_pattern = os.path.join(NEW_VIDEO_DIR, f"{user_id}_fire_*.mp4")
        smoke_pattern = os.path.join(NEW_VIDEO_DIR, f"{user_id}_smoke_*.mp4")
        
        fire_files = glob.glob(fire_pattern)
        smoke_files = glob.glob(smoke_pattern)
        
        if fire_files and smoke_files:
            # 获取最新的文件
            latest_fire = max(fire_files, key=os.path.getctime)
            latest_smoke = max(smoke_files, key=os.path.getctime)
            
            video_urls = {
                "video1": url_for('send_video_by_name', filename=os.path.basename(latest_fire)),
                "video2": url_for('send_video_by_name', filename=os.path.basename(latest_smoke))
            }

    return render_template('member.html', user=current_user, files=files, video_urls=video_urls)


# @app.route('/send_video/<int:video_id>')
# def send_video(video_id):
#     # 这个路由现在主要用于向后兼容或其他特殊情况
#     if current_user.is_authenticated:
#         user_id = current_user.id
#     else:
#         user_id = 'anonymous'

#     # 查找最新的视频文件
#     import glob
#     if video_id == 1:
#         pattern = os.path.join(NEW_VIDEO_DIR, f"{user_id}_fire_*.mp4")
#     elif video_id == 2:
#         pattern = os.path.join(NEW_VIDEO_DIR, f"{user_id}_smoke_*.mp4")
#     else:
#         return abort(404)
    
#     files = glob.glob(pattern)
#     if not files:
#         return abort(404)
    
#     # 获取最新的文件
#     latest_file = max(files, key=os.path.getctime)
#     return send_file(latest_file, mimetype='video/mp4')



@app.route('/error')
def error_page():
    msg = request.args.get('msg', '發生錯誤')
    return render_template('error.html', message=msg)

@app.route('/debug_session')
def debug_session():
    if current_user.is_authenticated:
        return f"User ID: {current_user.id}, Is Authenticated: {current_user.is_authenticated}"
    else:
        return "User is not authenticated"
    
# 在你的 routes.py 中應該已經有這個，如果沒有就加上
@app.route('/logout')
@login_required
def logout():
    
    # 執行登出
    logout_user()
    
    # 重導向到首頁
    return redirect(url_for('index'))
