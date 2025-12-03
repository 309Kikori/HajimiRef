import json
import base64

class MainViewModel:
    def read_image_file(self, path):
        """
        读取图片文件并返回二进制数据
        Reads an image file and returns binary data
        """
        try:
            with open(path, "rb") as f:
                return f.read()
        except Exception as e:
            print(f"Error reading file {path}: {e}")
            return None

    def save_board_data(self, path, items_data):
        """
        保存看板数据到 JSON 文件
        Saves the board data to a JSON file
        """
        data = {
            "version": 2,
            "images": items_data
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
            return True, None
        except Exception as e:
            return False, str(e)

    def load_board_data(self, path):
        """
        从 JSON 文件加载看板数据，并解码 Base64 图片数据
        Loads board data from a JSON file and decodes Base64 image data
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            images = []
            for img_data in data.get("images", []):
                b64_data = img_data.get("data")
                if b64_data:
                    try:
                        img_bytes = base64.b64decode(b64_data)
                        images.append({
                            "x": img_data.get("x", 0),
                            "y": img_data.get("y", 0),
                            "scale": img_data.get("scale", 1.0),
                            "data": img_bytes
                        })
                    except Exception as decode_err:
                        print(f"Error decoding image data: {decode_err}")
                        continue
            return True, images
        except Exception as e:
            return False, str(e)
