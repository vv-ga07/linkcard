"""audioicon.pngから白背景を削除して透過画像を作成"""
from PIL import Image

def remove_white_background(input_file, output_file, threshold=240):
    """
    画像から白背景を削除して透過PNGを作成
    
    Args:
        input_file: 入力画像ファイル
        output_file: 出力画像ファイル（透過PNG）
        threshold: 白判定の閾値（0-255、この値以上を白として透明化）
    """
    # 画像を開く
    img = Image.open(input_file)
    img = img.convert('RGBA')
    
    # ピクセルデータを取得
    datas = img.getdata()
    
    newData = []
    for item in datas:
        # 白に近い色（RGB全てがthreshold以上）を透明にする
        if item[0] >= threshold and item[1] >= threshold and item[2] >= threshold:
            # 完全透明にする
            newData.append((255, 255, 255, 0))
        else:
            # そのまま保持
            newData.append(item)
    
    # 新しいデータを設定
    img.putdata(newData)
    
    # 実際に描画されている部分だけを切り抜く
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
        print(f"切り抜き後のサイズ: {img.width}x{img.height}")
    
    # 保存
    img.save(output_file, 'PNG')
    print(f"✅ 背景を削除して保存しました: {output_file}")
    print(f"元のサイズからの変化: 切り抜き済み")

if __name__ == "__main__":
    # 白背景を削除（閾値240: かなり白に近い色を透明化）
    remove_white_background('audioicon.png', 'audioicon_transparent.png', threshold=240)
