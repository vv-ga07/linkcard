"""リンクカード用の画像に再生ボタンと暗いオーバーレイを追加"""
from PIL import Image, ImageDraw

def create_linkcard_image(input_file, output_file, target_width=1200, target_height=630, offset_y=50):
    """
    リンクカード用画像を生成（再生ボタン付き）
    
    Args:
        input_file: 入力画像ファイル
        output_file: 出力画像ファイル
        target_width: 目標幅
        target_height: 目標高さ
        offset_y: 切り取り開始位置のオフセット
    """
    # 元画像を読み込み
    img = Image.open(input_file)
    print(f"元画像サイズ: {img.width}x{img.height}")
    
    # 横幅を1200pxに合わせて拡大・縮小
    ratio = target_width / img.width
    new_height = int(img.height * ratio)
    resized = img.resize((target_width, new_height), Image.Resampling.LANCZOS)
    print(f"リサイズ後: {target_width}x{new_height}")
    
    # 指定位置から切り取り
    if new_height >= target_height + offset_y:
        cropped = resized.crop((0, offset_y, target_width, target_height + offset_y))
        print(f"切り取り: Y={offset_y}から{target_height + offset_y}")
    else:
        cropped = Image.new('RGB', (target_width, target_height), (255, 255, 255))
        cropped.paste(resized, (0, 0))
    
    # RGBAモードに変換（透過処理のため）
    img_rgba = cropped.convert('RGBA')
    
    # 暗いオーバーレイを追加（25%の黒）
    overlay = Image.new('RGBA', (target_width, target_height), (0, 0, 0, 64))  # alpha=64は約25%
    img_with_overlay = Image.alpha_composite(img_rgba, overlay)
    
    # カスタムアイコンを読み込み
    try:
        icon = Image.open('audioicon.png')
        # RGBAに変換
        if icon.mode != 'RGBA':
            icon = icon.convert('RGBA')
        
        # 不要な背景を切り抜く（透明でない部分だけを抽出）
        # アルファチャンネルがない場合、白背景を透明にする
        if icon.mode == 'RGBA':
            # アルファチャンネルを使用してバウンディングボックスを取得
            bbox = icon.getbbox()
        else:
            # 白または特定の色を透明として扱う
            icon = icon.convert('RGBA')
            datas = icon.getdata()
            newData = []
            for item in datas:
                # 白に近い色を透明にする
                if item[0] > 240 and item[1] > 240 and item[2] > 240:
                    newData.append((255, 255, 255, 0))
                else:
                    newData.append(item)
            icon.putdata(newData)
            bbox = icon.getbbox()
        
        # 切り抜き
        if bbox:
            icon = icon.crop(bbox)
            print(f"切り抜き後のアイコンサイズ: {icon.width}x{icon.height}")
        
        # アイコンのサイズを調整（4倍に拡大：150 → 600）
        icon_size = 600
        icon.thumbnail((icon_size, icon_size), Image.Resampling.LANCZOS)
        
        # 中央に配置
        center_x = target_width // 2
        center_y = target_height // 2
        icon_x = center_x - icon.width // 2
        icon_y = center_y - icon.height // 2
        
        # アイコンを合成
        img_with_overlay.paste(icon, (icon_x, icon_y), icon)
        print(f"✅ カスタムアイコン追加: {icon.width}x{icon.height}")
        
    except Exception as e:
        print(f"⚠️ アイコンの読み込みに失敗: {e}")
        # フォールバック: デフォルトの再生ボタンを描画
        draw = ImageDraw.Draw(img_with_overlay, 'RGBA')
        center_x = target_width // 2
        center_y = target_height // 2
        circle_radius = 50
        draw.ellipse(
            [center_x - circle_radius, center_y - circle_radius,
             center_x + circle_radius, center_y + circle_radius],
            fill=(255, 255, 255, 180),
            outline=(255, 255, 255, 200),
            width=2
        )
        triangle_size = 25
        offset_x = 5
        triangle = [
            (center_x - triangle_size//2 + offset_x, center_y - triangle_size),
            (center_x - triangle_size//2 + offset_x, center_y + triangle_size),
            (center_x + triangle_size + offset_x, center_y)
        ]
        draw.polygon(triangle, fill=(60, 60, 60, 255))
    
    # RGBに変換して保存
    final_img = img_with_overlay.convert('RGB')
    final_img.save(output_file, 'PNG', quality=95)
    print(f"✅ 再生ボタン付きカードを生成: {output_file}")

if __name__ == "__main__":
    create_linkcard_image('card_image.jpg', 'card_image_v2.png', offset_y=50)
