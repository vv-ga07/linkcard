import asyncio
import sys
from pathlib import Path
from urllib.parse import urlparse, urljoin
from playwright.async_api import async_playwright
from PIL import Image, ImageDraw, ImageFont
import io
import requests

class MetadataFetcher:
    """URLからメタデータを取得するクラス（OGPフォールバック対応）"""
    
    async def fetch(self, url: str) -> dict:
        """メタデータを取得"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                await page.goto(url, wait_until='networkidle', timeout=30000)
                await page.wait_for_timeout(500)
                
                metadata = {
                    'title': await self._get_title(page, url),
                    'description': await self._get_description(page),
                    'image': await self._get_image(page, url),
                    'url': url
                }
                
                return metadata
                
            except Exception as e:
                print(f"エラー: {e}")
                return self._get_fallback_metadata(url)
            finally:
                await browser.close()
    
    async def _get_title(self, page, url: str) -> str:
        """タイトルを優先順位付きで取得"""
        selectors = [
            'meta[property="og:title"]',
            'meta[name="twitter:title"]',
            'meta[property="og:site_name"]',
            'title',
            'h1'
        ]
        
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    if 'meta' in selector:
                        content = await element.get_attribute('content')
                    else:
                        content = await element.inner_text()
                    
                    if content and content.strip():
                        return content.strip()
            except:
                continue
        
        # デフォルト: ドメイン名
        return urlparse(url).netloc
    
    async def _get_description(self, page) -> str:
        """説明文を優先順位付きで取得"""
        selectors = [
            'meta[property="og:description"]',
            'meta[name="twitter:description"]',
            'meta[name="description"]',
            'meta[itemprop="description"]'
        ]
        
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    content = await element.get_attribute('content')
                    if content and content.strip():
                        return content.strip()[:200]  # 最大200文字
            except:
                continue
        
        # フォールバック: 最初のpタグ
        try:
            p_element = await page.query_selector('p')
            if p_element:
                text = await p_element.inner_text()
                if text and text.strip():
                    return text.strip()[:200]
        except:
            pass
        
        return ""
    
    async def _get_image(self, page, url: str) -> str:
        """画像URLを優先順位付きで取得"""
        selectors = [
            'meta[property="og:image"]',
            'meta[name="twitter:image"]',
            'meta[itemprop="image"]',
            'link[rel="image_src"]'
        ]
        
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    if 'meta' in selector:
                        image_url = await element.get_attribute('content')
                    else:
                        image_url = await element.get_attribute('href')
                    
                    if image_url:
                        # 相対URLを絶対URLに変換
                        return urljoin(url, image_url)
            except:
                continue
        
        return None
    
    def _get_fallback_metadata(self, url: str) -> dict:
        """フォールバックメタデータ"""
        parsed = urlparse(url)
        return {
            'title': parsed.netloc,
            'description': '',
            'image': None,
            'url': url
        }


class CardGenerator:
    """リンクカード画像を生成するクラス"""
    
    def __init__(self):
        self.width = 1200
        self.height = 630
        self.bg_color = (255, 255, 255)
        
    def generate(self, metadata: dict, output_path: str):
        """カード画像を生成"""
        # キャンバス作成
        img = Image.new('RGB', (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)
        
        # フォント設定（システムフォントを使用）
        try:
            title_font = ImageFont.truetype("msgothic.ttc", 48)
            desc_font = ImageFont.truetype("msgothic.ttc", 28)
            url_font = ImageFont.truetype("msgothic.ttc", 24)
        except:
            # フォントが見つからない場合はデフォルト
            title_font = ImageFont.load_default()
            desc_font = ImageFont.load_default()
            url_font = ImageFont.load_default()
        
        # サムネイル画像（左側）
        thumbnail_x = 50
        thumbnail_y = 50
        thumbnail_width = 400
        thumbnail_height = 530
        
        if metadata['image']:
            try:
                thumb_img = self._download_image(metadata['image'])
                if thumb_img:
                    # リサイズして配置
                    thumb_img = self._resize_image(thumb_img, thumbnail_width, thumbnail_height)
                    img.paste(thumb_img, (thumbnail_x, thumbnail_y))
                else:
                    # プレースホルダー
                    draw.rectangle(
                        [(thumbnail_x, thumbnail_y), 
                         (thumbnail_x + thumbnail_width, thumbnail_y + thumbnail_height)],
                        fill=(240, 240, 240),
                        outline=(200, 200, 200),
                        width=2
                    )
            except:
                # エラー時はプレースホルダー
                draw.rectangle(
                    [(thumbnail_x, thumbnail_y), 
                     (thumbnail_x + thumbnail_width, thumbnail_y + thumbnail_height)],
                    fill=(240, 240, 240),
                    outline=(200, 200, 200),
                    width=2
                )
        else:
            # 画像なしの場合はプレースホルダー
            draw.rectangle(
                [(thumbnail_x, thumbnail_y), 
                 (thumbnail_x + thumbnail_width, thumbnail_y + thumbnail_height)],
                fill=(240, 240, 240),
                outline=(200, 200, 200),
                width=2
            )
        
        # テキスト領域
        text_x = 500
        text_width = 650
        
        # タイトル
        title = metadata['title']
        title_y = 100
        self._draw_wrapped_text(
            draw, title, (text_x, title_y), text_width, 
            title_font, (51, 51, 51), max_lines=3
        )
        
        # 説明文
        if metadata['description']:
            desc_y = 300
            self._draw_wrapped_text(
                draw, metadata['description'], (text_x, desc_y), text_width,
                desc_font, (102, 102, 102), max_lines=4
            )
        
        # URL（ドメイン）
        domain = urlparse(metadata['url']).netloc
        url_y = 550
        draw.text((text_x, url_y), domain, font=url_font, fill=(153, 153, 153))
        
        # 保存
        img.save(output_path, 'PNG', quality=95)
        print(f"リンクカードを生成しました: {output_path}")
    
    def _download_image(self, url: str) -> Image.Image:
        """画像をダウンロード"""
        try:
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            if response.status_code == 200:
                return Image.open(io.BytesIO(response.content))
        except:
            pass
        return None
    
    def _resize_image(self, img: Image.Image, max_width: int, max_height: int) -> Image.Image:
        """画像をリサイズ（アスペクト比維持）"""
        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        return img
    
    def _draw_wrapped_text(self, draw, text: str, position: tuple, max_width: int, 
                           font, color: tuple, max_lines: int = 3):
        """折り返しテキストを描画"""
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = f"{current_line} {word}".strip()
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        # 最大行数で切り捨て
        lines = lines[:max_lines]
        if len(lines) == max_lines and len(text) > sum(len(l) for l in lines):
            lines[-1] = lines[-1][:50] + "..."
        
        # 描画
        y = position[1]
        for line in lines:
            draw.text((position[0], y), line, font=font, fill=color)
            bbox = draw.textbbox((0, 0), line, font=font)
            y += bbox[3] - bbox[1] + 10


class HTMLGenerator:
    """OGP対応HTMLファイルを生成するクラス"""
    
    def generate(self, metadata: dict, image_filename: str, output_path: str = "linkcard.html"):
        """OGPタグ付きHTMLファイルを生成"""
        html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    <!-- Open Graph / Facebook -->
    <meta property="og:type" content="website">
    <meta property="og:url" content="{metadata['url']}">
    <meta property="og:title" content="{self._escape_html(metadata['title'])}">
    <meta property="og:description" content="{self._escape_html(metadata['description'])}">
    <meta property="og:image" content="{image_filename}">
    
    <!-- Twitter -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:url" content="{metadata['url']}">
    <meta name="twitter:title" content="{self._escape_html(metadata['title'])}">
    <meta name="twitter:description" content="{self._escape_html(metadata['description'])}">
    <meta name="twitter:image" content="{image_filename}">
    
    <title>{self._escape_html(metadata['title'])}</title>
    
    <!-- 自動リダイレクト（3秒後） -->
    <meta http-equiv="refresh" content="3;url={metadata['url']}">
    
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background: #f5f5f5;
        }}
        .container {{
            text-align: center;
            padding: 40px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            max-width: 600px;
        }}
        h1 {{
            color: #333;
            margin-bottom: 20px;
        }}
        .redirect-message {{
            color: #666;
            margin-bottom: 20px;
        }}
        a {{
            color: #1da1f2;
            text-decoration: none;
            font-weight: bold;
        }}
        a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>リダイレクト中...</h1>
        <p class="redirect-message">3秒後に元のページに移動します。</p>
        <p>自動で移動しない場合は、<a href="{metadata['url']}">こちらをクリック</a>してください。</p>
    </div>
</body>
</html>"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"HTMLファイルを生成しました: {output_path}")
    
    def _escape_html(self, text: str) -> str:
        """HTMLエスケープ処理"""
        if not text:
            return ""
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&#39;'))


class LinkCardGenerator:
    """リンクカード生成のメインクラス"""
    
    def __init__(self):
        self.fetcher = MetadataFetcher()
        self.generator = CardGenerator()
        self.html_generator = HTMLGenerator()
    
    async def generate(self, url: str, output_path: str = "linkcard.png", generate_html: bool = False):
        """リンクカードを生成"""
        print(f"メタデータを取得中: {url}")
        metadata = await self.fetcher.fetch(url)
        
        print(f"タイトル: {metadata['title']}")
        print(f"説明: {metadata['description'][:50]}..." if metadata['description'] else "説明: なし")
        print(f"画像: {metadata['image']}" if metadata['image'] else "画像: なし")
        
        print("カード画像を生成中...")
        self.generator.generate(metadata, output_path)
        
        if generate_html:
            print("HTMLファイルを生成中...")
            # 画像ファイル名を取得（絶対URLに変換する必要がある場合は後で調整）
            image_filename = Path(output_path).name
            html_path = output_path.replace('.png', '.html')
            self.html_generator.generate(metadata, image_filename, html_path)
            print("\n📝 次のステップ:")
            print(f"1. {output_path} と {html_path} をWebサーバー（GitHub Pages等）にアップロード")
            print("2. アップロード先のHTMLファイルのURLをXに投稿")
            print("3. Xで自動的にリンクカードが表示されます")
            print(f"4. カードをクリックすると {url} に遷移します")


async def main():
    if len(sys.argv) < 2:
        print("使用方法: python linkcard_generator.py <URL> [-o 出力ファイル名] [--generate-html]")
        print("例: python linkcard_generator.py https://example.com")
        print("例: python linkcard_generator.py https://example.com -o card.png")
        print("例: python linkcard_generator.py https://example.com --generate-html")
        sys.exit(1)
    
    url = sys.argv[1]
    output_path = "linkcard.png"
    generate_html = False
    
    # オプション解析
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "-o" and i + 1 < len(sys.argv):
            output_path = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--generate-html":
            generate_html = True
            i += 1
        else:
            i += 1
    
    generator = LinkCardGenerator()
    await generator.generate(url, output_path, generate_html)


if __name__ == "__main__":
    asyncio.run(main())
